/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2026 Deep Shah
    Copyright (C) 2026 Colin B. Macdonald
*/

/**
 * This javascript routine provides interaction with small multiple choice boxes.
 *
 * The html template must have a canvas element with id `canvas`
 * and an img element with id `reference_image`.
 *
 * The template must define some variables using Django's `json_script` filter:
 * top_left_ref_coord, bottom_right_ref_coord.
 */

/* global
    mcq_box_detection_url
*/

const image = document.getElementById('reference_image');

(function () {
  const optionLabels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const overlay = document.getElementById('mcq_box_overlay');
  const controls = document.getElementById('mcq_controls');
  const detectButton = document.getElementById('mcq_detect_boxes');
  const addButton = document.getElementById('mcq_add_box');
  const removeButton = document.getElementById('mcq_remove_box');
  const clearButton = document.getElementById('mcq_clear_boxes');
  const autoLabelButton = document.getElementById('mcq_auto_label_boxes');
  const activeLabelSelect = document.getElementById('mcq_active_label');
  const optionCountContainer = document.getElementById('mcq_option_count');
  const optionCountInput = document.getElementById('mcq_num_options');
  const questionTypeInput = document.getElementById('question_type');
  const statusElement = document.getElementById('mcq_detection_status');
  const hiddenInput = document.getElementById('mcq_boxes');

  if (
    !overlay
    || !controls
    || !detectButton
    || !autoLabelButton
    || !activeLabelSelect
    || !optionCountContainer
    || !questionTypeInput
    || !hiddenInput
  ) {
    return;
  }

  let mcqBoxes = [];
  let activeBoxIndex = -1;
  let dragState = null;

  /**
   * Clamp a value to an inclusive numeric range.
   * @param {number} value - Value to constrain.
   * @param {number} low - Inclusive lower bound.
   * @param {number} high - Inclusive upper bound.
   * @returns {number} - Constrained value.
   */
  function clamp(value, low, high) {
    return Math.min(Math.max(value, low), high);
  }

  /**
   * Round a normalized coordinate to the storage precision.
   * @param {number} value - Coordinate to round.
   * @returns {number} - Coordinate rounded to six decimal places.
   */
  function roundCoord(value) {
    return Number(value.toFixed(6));
  }

  /**
   * Convert a canvas-pixel delta to normalized Plom QR coordinates.
   * @param {number} dx - Horizontal canvas delta in pixels.
   * @param {number} dy - Vertical canvas delta in pixels.
   * @returns {object} - Horizontal/vertical deltas in Plom QR coordinates keyed by "dx" and "dy".
   * Accesses global variable `image`.  Doesn't actually use `canvas` but
   * assumes they have the same size (or something like that: I had some
   * trouble with both this file and rectangle_select.js accessing `canvas`).
   */
  function canvasDeltaToPlom(dx, dy) {
    const top_left_coord = JSON.parse(document.getElementById('top_left_ref_coord').textContent);
    const bottom_right_coord = JSON.parse(document.getElementById('bottom_right_ref_coord').textContent);
    const refwidth = bottom_right_coord[0] - top_left_coord[0];
    const refheight = bottom_right_coord[1] - top_left_coord[1];
    return {
      dx: (dx * image.naturalWidth / image.width) / refwidth,
      dy: (dy * image.naturalHeight / image.height) / refheight,
    };
  }

  /**
   * Convert a normalized Plom QR-coord box to a canvas-pixel rectangle.
   * @param {object} box - Box in normalized Plom QR coordinates.
   * @returns {object} - Rectangle positioned and sized in canvas pixels.
   * Accesses global variables `image` and `canvas`.
   */
  function plomBoxToCanvasBox(box) {
    const top_left_coord = JSON.parse(document.getElementById('top_left_ref_coord').textContent);
    const bottom_right_coord = JSON.parse(document.getElementById('bottom_right_ref_coord').textContent);
    const refwidth = bottom_right_coord[0] - top_left_coord[0];
    const refheight = bottom_right_coord[1] - top_left_coord[1];

    const absLeft = top_left_coord[0] + box.left * refwidth;
    const absTop = top_left_coord[1] + box.top * refheight;
    const absRight = top_left_coord[0] + box.right * refwidth;
    const absBottom = top_left_coord[1] + box.bottom * refheight;
    return {
      left: absLeft * image.width / image.naturalWidth,
      top: absTop * image.height / image.naturalHeight,
      width: (absRight - absLeft) * image.width / image.naturalWidth,
      height: (absBottom - absTop) * image.height / image.naturalHeight,
    };
  }

  /**
   * Return the normalized selected rectangle, or null when it is invalid.
   * @returns {object | null} - Valid selected rectangle or null.
   */
  function getSelectedRect() {
    const selected = {
      left: parseFloat(document.getElementById('plom_left').value),
      top: parseFloat(document.getElementById('plom_top').value),
      right: parseFloat(document.getElementById('plom_right').value),
      bottom: parseFloat(document.getElementById('plom_bottom').value),
    };
    if (
      !Number.isFinite(selected.left)
      || !Number.isFinite(selected.top)
      || !Number.isFinite(selected.right)
      || !Number.isFinite(selected.bottom)
    ) {
      return null;
    }
    const selectedRect = {
      left: Math.min(selected.left, selected.right),
      top: Math.min(selected.top, selected.bottom),
      right: Math.max(selected.left, selected.right),
      bottom: Math.max(selected.top, selected.bottom),
    };
    if (
      selectedRect.right <= selectedRect.left
      || selectedRect.bottom <= selectedRect.top
    ) {
      return null;
    }
    return selectedRect;
  }

  /**
   * Return the requested option count within the supported range.
   * @returns {number} - Number of MCQ options.
   */
  function getNumOptions() {
    return clamp(parseInt(optionCountInput.value, 10) || 1, 1, optionLabels.length);
  }

  /**
   * Return the option labels allowed by the current option count.
   * @returns {string[]} - Allowed option labels.
   */
  function getAllowedLabels() {
    return optionLabels.slice(0, getNumOptions()).split('');
  }

  /**
   * Return a stable sorting rank for an option label.
   * @param {string} label - Option label to rank.
   * @returns {number} - Zero-based label rank or the fallback rank.
   */
  function getLabelRank(label) {
    const rank = optionLabels.indexOf(label);
    return rank >= 0 ? rank : optionLabels.length;
  }

  /**
   * Return whether the clustering form is currently in MCQ mode.
   * @returns {boolean} - True when MCQ controls should be active.
   */
  function isMCQMode() {
    return questionTypeInput.value === 'MCQ';
  }

  /**
   * Update the detection status message and error styling.
   * @param {string} message - Status text to display.
   * @param {boolean} isError - Whether to apply error styling.
   */
  function setStatus(message, isError) {
    statusElement.textContent = message;
    statusElement.classList.toggle('text-danger', Boolean(isError));
    statusElement.classList.toggle('text-muted', !isError);
  }

  /**
   * Check whether an option box lies within the selected rectangle.
   * @param {object} selectedRect - Bounding rectangle for all option boxes.
   * @param {object} box - Option box to check.
   * @returns {boolean} - True when the box is fully contained.
   */
  function selectedRectContainsBox(selectedRect, box) {
    const tolerance = 0.000001;
    return (
      box.left >= selectedRect.left - tolerance
      && box.top >= selectedRect.top - tolerance
      && box.right <= selectedRect.right + tolerance
      && box.bottom <= selectedRect.bottom + tolerance
    );
  }

  /**
   * Return all option boxes that lie outside the selected rectangle.
   * @param {object} selectedRect - Bounding rectangle for all option boxes.
   * @returns {object[]} - Option boxes outside the selected rectangle.
   */
  function getBoxesOutsideSelectedRect(selectedRect) {
    return mcqBoxes.filter(box => !selectedRectContainsBox(selectedRect, box));
  }

  /**
   * Build the validation message for boxes outside the selection.
   * @param {object[]} boxes - Option boxes outside the selected rectangle.
   * @returns {string} - User-facing validation message.
   */
  function boxOutsideMessage(boxes) {
    const labels = boxes.map(box => box.label).join(', ');
    const plural = boxes.length === 1 ? '' : 'es';
    return `Option box${plural} ${labels} must stay inside the selected rectangle.`;
  }

  /**
   * Constrain an option box to the selected rectangle.
   * @param {object} box - Option box to constrain.
   * @param {object} selectedRect - Bounding rectangle for the option box.
   * @returns {object} - Constrained option box.
   */
  function clampBoxToSelectedRect(box, selectedRect) {
    const selectedWidth = selectedRect.right - selectedRect.left;
    const selectedHeight = selectedRect.bottom - selectedRect.top;
    const width = Math.min(box.right - box.left, selectedWidth);
    const height = Math.min(box.bottom - box.top, selectedHeight);
    const left = clamp(box.left, selectedRect.left, selectedRect.right - width);
    const top = clamp(box.top, selectedRect.top, selectedRect.bottom - height);
    return {
      ...box,
      left,
      top,
      right: left + width,
      bottom: top + height,
    };
  }

  /**
   * Validate that every MCQ option box stays inside the selection.
   * @returns {boolean} - True when every option box is valid.
   */
  function validateBoxesInsideSelectedRect() {
    if (!isMCQMode() || mcqBoxes.length === 0) {
      return true;
    }
    const selectedRect = getSelectedRect();
    if (!selectedRect) {
      setStatus('Select a rectangle before submitting MCQ boxes.', true);
      return false;
    }
    const outsideBoxes = getBoxesOutsideSelectedRect(selectedRect);
    if (outsideBoxes.length > 0) {
      setStatus(boxOutsideMessage(outsideBoxes), true);
      return false;
    }
    return true;
  }

  /**
   * Validate that option-box labels are allowed and unique.
   * @returns {boolean} - True when every label is valid and unique.
   */
  function validateBoxLabels() {
    if (!isMCQMode() || mcqBoxes.length === 0) {
      return true;
    }
    const allowedLabels = new Set(getAllowedLabels());
    const seenLabels = new Set();
    for (const box of mcqBoxes) {
      if (!allowedLabels.has(box.label)) {
        setStatus(
          `Option box ${box.label} is not valid for ${getNumOptions()} options.`,
          true,
        );
        return false;
      }
      if (seenLabels.has(box.label)) {
        setStatus(`Option label ${box.label} is used more than once.`, true);
        return false;
      }
      seenLabels.add(box.label);
    }
    return true;
  }

  /** Align the option-box overlay with the image. */
  function syncOverlayToCanvas() {
    overlay.style.top = image.offsetTop + 'px';
    overlay.style.left = image.offsetLeft + 'px';
    overlay.style.width = `${image.width}px`;
    overlay.style.height = `${image.height}px`;
  }

  /**
   * Convert an option box to the rounded submission payload shape.
   * @param {object} box - Option box to serialize.
   * @returns {object} - Rounded option-box payload.
   */
  function serialiseBox(box) {
    return {
      label: box.label,
      left: roundCoord(box.left),
      top: roundCoord(box.top),
      right: roundCoord(box.right),
      bottom: roundCoord(box.bottom),
    };
  }

  /**
   * Return option boxes in deterministic submission order.
   * @returns {object[]} - Option boxes sorted by label and position.
   */
  function getBoxesForSubmission() {
    return [...mcqBoxes].sort((a, b) => {
      const labelOrder = getLabelRank(a.label) - getLabelRank(b.label);
      if (labelOrder !== 0) {
        return labelOrder;
      }
      if (a.top === b.top) {
        return a.left - b.left;
      }
      return a.top - b.top;
    });
  }

  /** Serialize the current MCQ box selection into the hidden form field. */
  function updateHiddenInput() {
    if (!isMCQMode()) {
      hiddenInput.value = '[]';
      return;
    }
    hiddenInput.value = JSON.stringify({
      question_type: questionTypeInput.value,
      num_options: getNumOptions(),
      boxes: getBoxesForSubmission().map(serialiseBox),
    });
  }

  /**
   * Sort option boxes from left to right within top-to-bottom rows.
   * @param {object[]} boxes - Option boxes to sort.
   * @returns {object[]} - Option boxes in visual reading order.
   */
  function sortBoxesInReadingOrder(boxes) {
    const sortedByTop = [...boxes].sort((a, b) => {
      if (a.top === b.top) {
        return a.left - b.left;
      }
      return a.top - b.top;
    });
    if (sortedByTop.length === 0) {
      return [];
    }

    const heights = sortedByTop
      .map(box => box.bottom - box.top)
      .sort((a, b) => a - b);
    const medianHeight = heights[Math.floor(heights.length / 2)];
    const rowThreshold = Math.max(medianHeight * 0.75, 0.01);
    const rows = [];

    sortedByTop.forEach((box) => {
      const centerY = (box.top + box.bottom) / 2;
      let row = rows.find(candidate => (
        Math.abs(centerY - candidate.centerY) <= rowThreshold
      ));
      if (!row) {
        row = { centerY, boxes: [] };
        rows.push(row);
      }
      row.boxes.push(box);
      row.centerY = row.boxes.reduce(
        (total, rowBox) => total + (rowBox.top + rowBox.bottom) / 2,
        0,
      ) / row.boxes.length;
    });

    return rows
      .sort((a, b) => a.centerY - b.centerY)
      .flatMap(row => row.boxes.sort((a, b) => a.left - b.left));
  }

  /** Assign option labels according to visual reading order. */
  function autoLabelBoxes() {
    const activeBox = activeBoxIndex >= 0 ? mcqBoxes[activeBoxIndex] : null;
    mcqBoxes = sortBoxesInReadingOrder(mcqBoxes);
    mcqBoxes.forEach((box, index) => {
      box.label = optionLabels[index] || '?';
    });
    activeBoxIndex = activeBox ? mcqBoxes.indexOf(activeBox) : activeBoxIndex;
  }

  /**
   * Return the first label not already assigned to an option box.
   * @returns {string} - First unused label or the unknown-label marker.
   */
  function getFirstUnusedLabel() {
    const usedLabels = new Set(mcqBoxes.map(box => box.label));
    return getAllowedLabels().find(label => !usedLabels.has(label)) || '?';
  }

  /** Refresh the active-box label selector and its enabled state. */
  function updateActiveLabelSelect() {
    const activeBox = activeBoxIndex >= 0 ? mcqBoxes[activeBoxIndex] : null;
    activeLabelSelect.replaceChildren();

    const emptyOption = new Option('Select', '');
    activeLabelSelect.appendChild(emptyOption);
    getAllowedLabels().forEach((label) => {
      activeLabelSelect.appendChild(new Option(label, label));
    });

    activeLabelSelect.disabled = !isMCQMode() || !activeBox;
    activeLabelSelect.value = activeBox && getAllowedLabels().includes(activeBox.label)
      ? activeBox.label
      : '';
  }

  /**
   * Select an option box by array index.
   * @param {number} index - Index of the option box to activate.
   */
  function setActiveBox(index) {
    activeBoxIndex = index >= 0 && index < mcqBoxes.length ? index : -1;
    updateActiveLabelSelect();
  }

  /**
   * Assign a label to the active box and swap an existing duplicate.
   * @param {string} label - Label to assign to the active box.
   */
  function setActiveBoxLabel(label) {
    if (activeBoxIndex < 0 || activeBoxIndex >= mcqBoxes.length || !label) {
      return;
    }
    const activeBox = mcqBoxes[activeBoxIndex];
    const previousLabel = activeBox.label;
    const otherIndex = mcqBoxes.findIndex(
      (box, index) => index !== activeBoxIndex && box.label === label,
    );
    activeBox.label = label;
    if (otherIndex >= 0 && previousLabel !== '?') {
      mcqBoxes[otherIndex].label = previousLabel;
    }
    renderBoxes();
  }

  /** Render all option boxes and synchronize the form payload. */
  function renderBoxes() {
    syncOverlayToCanvas();
    overlay.replaceChildren();
    if (!isMCQMode()) {
      updateHiddenInput();
      return;
    }
    mcqBoxes.forEach((box, index) => {
      const canvasBox = plomBoxToCanvasBox(box);
      const boxElement = document.createElement('div');
      boxElement.className = 'mcq-option-box';
      if (index === activeBoxIndex) {
        boxElement.classList.add('active');
      }
      boxElement.dataset.index = index;
      boxElement.style.left = `${canvasBox.left}px`;
      boxElement.style.top = `${canvasBox.top}px`;
      boxElement.style.width = `${canvasBox.width}px`;
      boxElement.style.height = `${canvasBox.height}px`;
      boxElement.title = `Option ${box.label}`;

      const labelElement = document.createElement('span');
      labelElement.className = 'mcq-option-label';
      labelElement.textContent = box.label;
      boxElement.appendChild(labelElement);

      const resizeElement = document.createElement('span');
      resizeElement.className = 'mcq-option-resize';
      resizeElement.dataset.resize = 'true';
      boxElement.appendChild(resizeElement);

      boxElement.addEventListener('pointerdown', startDraggingBox);
      overlay.appendChild(boxElement);
    });
    updateActiveLabelSelect();
    updateHiddenInput();
  }

  /**
   * Begin moving or resizing the selected option box.
   * @param {PointerEvent} event - Pointer-down event on an option box.
   */
  function startDraggingBox(event) {
    const boxElement = event.currentTarget;
    setActiveBox(parseInt(boxElement.dataset.index, 10));
    event.preventDefault();
    event.stopPropagation();
    const selectedRect = getSelectedRect();
    if (!selectedRect) {
      setStatus('Select a rectangle before moving option boxes.', true);
      return;
    }
    mcqBoxes[activeBoxIndex] = clampBoxToSelectedRect(
      mcqBoxes[activeBoxIndex],
      selectedRect,
    );
    dragState = {
      mode: event.target.dataset.resize === 'true' ? 'resize' : 'move',
      startX: event.clientX,
      startY: event.clientY,
      original: { ...mcqBoxes[activeBoxIndex] },
      selectedRect,
    };
    renderBoxes();
  }

  /**
   * Apply pointer movement to the active option box.
   * @param {PointerEvent} event - Pointer-move event for the drag operation.
   */
  function moveActiveBox(event) {
    if (!dragState || activeBoxIndex < 0) {
      return;
    }

    const delta = canvasDeltaToPlom(
      event.clientX - dragState.startX,
      event.clientY - dragState.startY,
    );
    const original = dragState.original;
    const minDelta = canvasDeltaToPlom(12, 12);
    const box = mcqBoxes[activeBoxIndex];
    const selectedRect = dragState.selectedRect;

    if (dragState.mode === 'resize') {
      const maxWidth = selectedRect.right - original.left;
      const maxHeight = selectedRect.bottom - original.top;
      const minWidth = Math.min(minDelta.dx, maxWidth);
      const minHeight = Math.min(minDelta.dy, maxHeight);
      box.right = clamp(
        original.right + delta.dx,
        original.left + minWidth,
        selectedRect.right,
      );
      box.bottom = clamp(
        original.bottom + delta.dy,
        original.top + minHeight,
        selectedRect.bottom,
      );
    }
    else {
      const width = original.right - original.left;
      const height = original.bottom - original.top;
      box.left = clamp(
        original.left + delta.dx,
        selectedRect.left,
        selectedRect.right - width,
      );
      box.top = clamp(
        original.top + delta.dy,
        selectedRect.top,
        selectedRect.bottom - height,
      );
      box.right = box.left + width;
      box.bottom = box.top + height;
    }

    event.preventDefault();
    renderBoxes();
  }

  /** Finish the current option-box drag operation. */
  function finishDraggingBox() {
    if (!dragState) {
      return;
    }
    dragState = null;
    setActiveBox(
      mcqBoxes.length > 0 ? Math.min(activeBoxIndex, mcqBoxes.length - 1) : -1,
    );
    renderBoxes();
  }

  /**
   * Normalize a detected option box and constrain it to the selection.
   * @param {object} box - Detected option box from the server.
   * @param {object} selectedRect - Bounding rectangle for the option box.
   * @returns {object} - Normalized and constrained option box.
   */
  function normaliseDetectedBox(box, selectedRect) {
    return clampBoxToSelectedRect({
      label: box.label,
      left: clamp(box.plom.left, 0, 1),
      top: clamp(box.plom.top, 0, 1),
      right: clamp(box.plom.right, 0, 1),
      bottom: clamp(box.plom.bottom, 0, 1),
    }, selectedRect);
  }

  /** Request automatic option-box detection for the selected rectangle. */
  function detectBoxes() {
    if (!isMCQMode()) {
      return;
    }
    const selectedRect = getSelectedRect();
    if (!selectedRect) {
      setStatus('Select a rectangle before detecting boxes.', true);
      return;
    }

    const params = new URLSearchParams({
      left: selectedRect.left,
      top: selectedRect.top,
      right: selectedRect.right,
      bottom: selectedRect.bottom,
      num_options: getNumOptions(),
    });

    setStatus('Detecting boxes...', false);
    fetch(`${mcq_box_detection_url}?${params.toString()}`, {
      headers: { Accept: 'application/json' },
    })
      .then((response) => {
        if (!response.ok) {
          return response.text().then((text) => {
            throw new Error(text || response.statusText);
          });
        }
        return response.json();
      })
      .then((data) => {
        if (data.error) {
          throw new Error(data.error);
        }
        mcqBoxes = data.boxes.map(box => normaliseDetectedBox(box, selectedRect));
        setActiveBox(mcqBoxes.length > 0 ? 0 : -1);
        autoLabelBoxes();
        renderBoxes();
        if (mcqBoxes.length === getNumOptions()) {
          setStatus(`Detected ${mcqBoxes.length} boxes.`, false);
        }
        else {
          setStatus(`Detected ${mcqBoxes.length} of ${getNumOptions()} boxes.`, false);
        }
      })
      .catch((error) => {
        setStatus(error.message || 'Could not detect boxes.', true);
      });
  }

  /**
   * Determine a suitable size for a newly added option box.
   * @param {object} selectedRect - Bounding rectangle for the new option box.
   * @returns {object} - Suggested width and height in Plom coordinates.
   */
  function getDefaultBoxSize(selectedRect) {
    if (mcqBoxes.length > 0) {
      const widths = mcqBoxes
        .map(box => box.right - box.left)
        .sort((a, b) => a - b);
      const heights = mcqBoxes
        .map(box => box.bottom - box.top)
        .sort((a, b) => a - b);
      const middle = Math.floor(mcqBoxes.length / 2);
      return {
        width: widths[middle],
        height: heights[middle],
      };
    }
    const selectedHeight = selectedRect.bottom - selectedRect.top;
    const selectedWidth = selectedRect.right - selectedRect.left;
    const size = Math.min(selectedHeight * 0.35, selectedWidth * 0.12);
    return { width: size, height: size };
  }

  /** Add a new option box within the selected rectangle. */
  function addBox() {
    if (!isMCQMode()) {
      return;
    }
    const selectedRect = getSelectedRect();
    if (!selectedRect) {
      setStatus('Select a rectangle before adding a box.', true);
      return;
    }
    if (mcqBoxes.length >= getNumOptions()) {
      setStatus('Increase the option count before adding another box.', true);
      return;
    }
    const size = getDefaultBoxSize(selectedRect);
    const boxWidth = Math.min(size.width, selectedRect.right - selectedRect.left);
    const boxHeight = Math.min(size.height, selectedRect.bottom - selectedRect.top);
    const optionSlot = Math.min(mcqBoxes.length + 1, getNumOptions());
    const slotGap = (selectedRect.right - selectedRect.left) / (getNumOptions() + 1);
    const centerX = selectedRect.left + slotGap * optionSlot;
    const centerY = selectedRect.top + (selectedRect.bottom - selectedRect.top) / 2;
    const left = clamp(
      centerX - boxWidth / 2,
      selectedRect.left,
      selectedRect.right - boxWidth,
    );
    const top = clamp(
      centerY - boxHeight / 2,
      selectedRect.top,
      selectedRect.bottom - boxHeight,
    );
    mcqBoxes.push({
      label: getFirstUnusedLabel(),
      left,
      top,
      right: left + boxWidth,
      bottom: top + boxHeight,
    });
    setActiveBox(mcqBoxes.length - 1);
    renderBoxes();
    setStatus(`${mcqBoxes.length} boxes selected.`, false);
  }

  /** Remove the active option box. */
  function removeActiveBox() {
    if (activeBoxIndex < 0 || activeBoxIndex >= mcqBoxes.length) {
      return;
    }
    mcqBoxes.splice(activeBoxIndex, 1);
    setActiveBox(mcqBoxes.length > 0 ? 0 : -1);
    renderBoxes();
    setStatus(`${mcqBoxes.length} boxes selected.`, false);
  }

  /** Remove all option boxes. */
  function clearBoxes() {
    mcqBoxes = [];
    setActiveBox(-1);
    renderBoxes();
    setStatus('No boxes selected.', false);
  }

  /** Toggle MCQ controls and reset state when MCQ mode is disabled. */
  function updateMCQMode() {
    const enabled = isMCQMode();
    controls.classList.toggle('d-none', !enabled);
    optionCountContainer.classList.toggle('d-none', !enabled);
    overlay.classList.toggle('d-none', !enabled);
    if (!enabled) {
      mcqBoxes = [];
      setActiveBox(-1);
      setStatus('', false);
    }
    renderBoxes();
  }

  detectButton.addEventListener('click', detectBoxes);
  addButton.addEventListener('click', addBox);
  removeButton.addEventListener('click', removeActiveBox);
  clearButton.addEventListener('click', clearBoxes);
  autoLabelButton.addEventListener('click', () => {
    autoLabelBoxes();
    renderBoxes();
    setStatus(`${mcqBoxes.length} boxes labelled in reading order.`, false);
  });
  activeLabelSelect.addEventListener('change', () => {
    setActiveBoxLabel(activeLabelSelect.value);
  });
  optionCountInput.addEventListener('change', () => {
    updateActiveLabelSelect();
    updateHiddenInput();
  });
  questionTypeInput.addEventListener('change', updateMCQMode);
  document.addEventListener('pointermove', moveActiveBox);
  document.addEventListener('pointerup', finishDraggingBox);
  window.addEventListener('resize', renderBoxes);
  window.addEventListener('load', updateMCQMode);
  hiddenInput.form.addEventListener('submit', (event) => {
    if (!validateBoxesInsideSelectedRect()) {
      event.preventDefault();
      return;
    }
    if (!validateBoxLabels()) {
      event.preventDefault();
      return;
    }
    updateHiddenInput();
  });
  updateMCQMode();
})();
