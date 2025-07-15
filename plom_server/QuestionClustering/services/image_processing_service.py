import numpy as np
from skimage.transform import resize
import cv2
from collections import defaultdict


class ImageProcessingService:

    def addContrast(self, img, alpha: float, iterations: int):
        res = img.copy()
        for i in range(iterations):
            bg = cv2.GaussianBlur(res, (0, 0), sigmaX=15, sigmaY=15)
            clean = cv2.addWeighted(res, 1 + alpha, bg, -alpha, 0)
            res = np.clip(clean, 0, 255).astype(np.uint8)
        return res

    def get_connected_component_only(self, image, min_area: 30):
        # Compute CCs & stats
        _, labels, stats, _ = cv2.connectedComponentsWithStats(image, connectivity=8)

        # Get all areas
        areas = stats[:, cv2.CC_STAT_AREA]  # shape (n_labels,)

        # Build keep mask and explicitly drop background
        keep = areas >= min_area  # boolean array
        keep[0] = False  # label 0 is background → always drop

        # 4) Vectorized filtering in one pass
        filtered = (keep[labels]).astype(np.uint8) * 255

        return filtered

    def get_diff(
        self, blank_ref: np.ndarray, scanned: np.ndarray, dilation_iteration: int = 1
    ) -> np.ndarray:

        # Ensure grayscale
        if blank_ref.ndim == 3:
            blank_ref = cv2.cvtColor(blank_ref, cv2.COLOR_BGR2GRAY)

        if scanned.ndim == 3:
            scanned = cv2.cvtColor(scanned, cv2.COLOR_BGR2GRAY)

        if blank_ref.shape != scanned.shape:
            scanned = resize(
                scanned,
                (blank_ref.shape[0], blank_ref.shape[1]),
                anti_aliasing=True,
                preserve_range=True,
            ).astype(np.uint8)

        # Classifies x > 230 as background
        _, binarized_ref = cv2.threshold(
            blank_ref, thresh=230, maxval=255, type=cv2.THRESH_BINARY_INV
        )

        # Dilate reference ink so it can tolerate some noises
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated_ref = cv2.dilate(binarized_ref, kernel, iterations=dilation_iteration)

        addedContrast = self.addContrast(scanned, alpha=2, iterations=2)
        detail = cv2.GaussianBlur(addedContrast, (0, 0), sigmaX=1.5)
        sharp = cv2.addWeighted(addedContrast, 1.0, detail, -0.2, 0)

        binarized_scanned = cv2.adaptiveThreshold(
            sharp,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=25,
            C=20,
        )

        # Remove noises
        temp = cv2.morphologyEx(binarized_scanned, cv2.MORPH_OPEN, np.ones((2, 2)))
        cleaned_scanned = cv2.morphologyEx(temp, cv2.MORPH_CLOSE, np.ones((1, 2)))

        filtered = self.get_connected_component_only(cleaned_scanned, min_area=50)

        # Get the dif
        diff = cv2.bitwise_and(filtered, cv2.bitwise_not(dilated_ref))

        cleaned = cv2.morphologyEx(diff, cv2.MORPH_OPEN, np.ones((2, 2)))
        final = self.get_connected_component_only(cleaned, min_area=60)

        return final

    def merge_components_by_proximity(self, stats, tol):
        """Given stats from cv2.connectedComponentsWithStats,
        merge any components whose bounding-boxes are within tol pixels.
        Returns a list of groups; each group is a list of component labels.
        """

        def box_dist(b1, b2):
            x1, y1, w1, h1 = b1
            x2, y2, w2, h2 = b2
            dx = max(x2 - (x1 + w1), x1 - (x2 + w2), 0)
            dy = max(y2 - (y1 + h1), y1 - (y2 + h2), 0)
            return max(dx, dy)

        # collect non-background boxes
        boxes = [(lab, tuple(stats[lab][:4])) for lab in range(1, len(stats))]
        parent = {lab: lab for lab, _ in boxes}

        def find(u):
            while parent[u] != u:
                parent[u] = parent[parent[u]]
                u = parent[u]
            return u

        def union(u, v):
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[rv] = ru

        # union any pair closer than tol
        for i, (li, b1) in enumerate(boxes):
            for lj, b2 in boxes[i + 1 :]:
                if box_dist(b1, b2) <= tol:
                    union(li, lj)

        # collect final groups
        groups = defaultdict(list)
        for lab, _ in boxes:
            groups[find(lab)].append(lab)
        return list(groups.values())
