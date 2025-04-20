# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2025 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen
# Copyright (C) 2025 Aidan Murphy

"""Backend bits 'n bobs to talk to a Plom server."""

from __future__ import annotations

import hashlib
from io import BytesIO
import json
import logging
import mimetypes
import pathlib
import tempfile
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests
from requests_toolbelt import MultipartEncoder
from tqdm import tqdm

from plom.baseMessenger import BaseMessenger
from plom.scanMessenger import ScanMessenger
from plom.managerMessenger import ManagerMessenger
from plom.plom_exceptions import PlomSeriousException
from plom.plom_exceptions import (
    PlomAuthenticationException,
    PlomConflict,
    PlomNoBundle,
    PlomNoPaper,
    PlomNoPermission,
    PlomNoServerSupportException,
    PlomQuotaLimitExceeded,
    PlomRangeException,
    PlomTakenException,
    PlomTaskChangedError,
    PlomTaskDeletedError,
    PlomTimeoutError,
    PlomVersionMismatchException,
)

__all__ = [
    "Messenger",
    "ManagerMessenger",
    "ScanMessenger",
]

log = logging.getLogger("messenger")
# requests_log = logging.getLogger("urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True


class Messenger(BaseMessenger):
    """Handle communication with a Plom Server."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    # ------------------------
    # ------------------------
    # ID client API stuff

    def IDprogressCount(self) -> list[int]:
        """Return info about progress on identifying.

        Returns:
            list: with two integers, indicating the number of papers
            identified and the total number of papers to be identified.

        Raises:
            PlomAuthenticationException:
            PlomSeriousException: something unexpected happened.
        """
        with self.SRmutex:
            try:
                response = self.get(
                    "/ID/progress",
                    json={"user": self.user, "token": self.token},
                )
                # throw errors when response code != 200.
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def IDaskNextTask(self) -> int | None:
        """Return the paper number of a paper that needs IDing.

        Returns:
            Paper number or None if no papers need IDing.

        Raises:
            SeriousError: if something has unexpectedly gone wrong.
        """
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/ID/tasks/available",
                json={"user": self.user, "token": self.token},
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def IDrequestDoneTasks(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/ID/tasks/complete",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            idList = response.json()
            return idList
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    # ------------------------

    def IDclaimThisTask(self, code):
        with self.SRmutex:
            try:
                response = self.patch(
                    f"/ID/tasks/{code}",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                if response.status_code == 409:
                    raise PlomTakenException(response.reason)
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def IDreturnIDdTask(self, task, studentID, studentName):
        """Return a completed IDing task: identify a paper.

        Exceptions:
            PlomConflict: `studentID` already used on a different paper.
            PlomTakenException: someone else owns that task.  This is unexpected
                if you Claimed this task.
            PlomRangeException: no such test number or not yet scanned
            PlomAuthenticationException: login problems.
            PlomSeriousException: other errors.
        """
        with self.SRmutex:
            try:
                response = self.put(
                    f"/ID/tasks/{task}",
                    json={
                        "user": self.user,
                        "token": self.token,
                        "sid": studentID,
                        "sname": studentName,
                    },
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 409:
                    raise PlomConflict(response.reason) from None
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomTakenException(response.reason) from None
                if response.status_code == 404:
                    raise PlomRangeException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    # ------------------------
    # ------------------------
    # Marker stuff
    def MrequestDoneTasks(self, q: int, v: int) -> list[list[Any]]:
        """Information about the tasks previously marked by this year.

        Args:
            q: which question.
            v: which version.

        Returns:
            List of info the tasks.  Each entry is a list of the task
            string (of the form ``q0002g3``), the score, the time (in
            seconds), a list of tags (strings), and an "integrity code".
            An empty list is returned if nothing has been graded by this
            user.

        Deprecated: only for supporting legacy servers.
        """
        if not self.is_legacy_server():
            raise PlomNoServerSupportException(
                "Only legacy servers support list of tasks"
            )

        self.SRmutex.acquire()
        try:
            response = self.get(
                "/MK/tasks/complete",
                json={"user": self.user, "token": self.token, "q": q, "v": v},
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def get_tasks(
        self, qidx: int | None = None, v: int | None = None, *, username: str = ""
    ) -> list[list[Any]]:
        """Information about all tasks.

        Args:
            qidx: which question index, or None.
            v: which version, or None.

        Keyword Args:
            username: find the tasks assigned to a particular user.  If
                omitted we get the tasks for all users (and those unassigned)..

        Returns:
            List of info the tasks.  Each entry is a list of the task
            string (of the form ``q0002g3``), the score, the time (in
            seconds), a list of tags (strings), and which user its assigned to.
            An empty list is returned if there are no tasks.
            TODO: right now it might be a list-of-dicts.
        """
        if self.is_legacy_server():
            raise PlomNoServerSupportException(
                "Legacy server does not support list of tasks"
            )

        with self.SRmutex:
            try:
                query_params = []
                if qidx is not None:
                    query_params.append(f"q={qidx}")
                if v is not None:
                    query_params.append(f"v={v}")
                if username:
                    query_params.append(f"username={username}")
                url = "/MK/tasks/all"
                if query_params:
                    url += "?" + "&".join(query_params)
                response = self.get_auth(url)
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def MprogressCount_legacy(self, q, v) -> list[int]:
        """Return info about progress on a particular question-version pair.

        Args:
            q (str/int): a question number.
            v (str/int): a version number.

        Returns:
            A list of two integers, indicating the number of questions
            graded and the total number of questions to be graded of
            this question-version pair.

        Raises:
            PlomRangeException: `q` or `v` is out of range.
            PlomAuthenticationException:
            PlomSeriousException: something unexpected happened, such as
                non-integer `q` or `v`.
        """
        with self.SRmutex:
            try:
                response = self.get(
                    "/MK/progress",
                    json={"user": self.user, "token": self.token, "q": q, "v": v},
                )
                # throw errors when response code != 200.
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 416:
                    raise PlomRangeException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def get_marking_progress(self, qidx: int, ver: int) -> dict[str, Any]:
        """Get a dict representing the progress and quota status of current marker.

        Args:
            qidx: which question.
            ver: which version.

        Returns:
            Dict with keys "total_tasks", "total_tasks_marked", "user_tasks_claimed",
            "user_tasks_marked", and "user_quota_limit"
        """
        if self.is_legacy_server():
            n, m = self.MprogressCount_legacy(qidx, ver)
            d = {"total_tasks": m, "total_tasks_marked": n, "user_quota_limit": None}
            return d

        with self.SRmutex:
            try:
                response = self.get_auth(f"/MK/progress/{qidx}/{ver}")
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def MaskNextTask(
        self,
        q: int,
        v: int,
        *,
        tags: list[str] | None = None,
        min_paper_num: int | None = None,
        max_paper_num: int | None = None,
    ) -> str | None:
        """Ask server for a new marking task, return tgv or None.

        Args:
            q: question number.
            v: version number.

        Keyword Args:
            tags: if any tasks have ANY of these tags, then we have a
                preference for those.  (But we will still accept tasks
                without any of these tags).
            min_paper_num: paper number must be at least this value.
                (On legacy servers, this is a soft preference not a hard
                requirement).
            max_paper_num: paper number must at most this value.
                (Ignored on legacy servers).

        Returns:
            Either the task string or ``None`` indicated no
            more tasks available.

        Raises:
            RuntimeError: on legacy servers, can can pass at most
                one tag.
            PlomAuthenticationException: auth-related troubles.
            PlomSeriousException: something unexpected happened.

        TODO: why are we using json for a string return?
        """
        self.SRmutex.acquire()
        try:
            if not self.is_legacy_server():
                url = f"/MK/tasks/available?q={q}&v={v}"
                if tags:
                    url += f"&tags={','.join(tags)}"
                if min_paper_num:
                    url += f"&min_paper_num={min_paper_num}"
                if max_paper_num:
                    url += f"&max_paper_num={max_paper_num}"
                response = self.get_auth(url)
            else:
                tag = None
                if tags:
                    if len(tags) > 1:
                        raise RuntimeError("Legacy servers accept at most one tag")
                    (tag,) = tags
                response = self.get(
                    "/MK/tasks/available",
                    json={
                        "user": self.user,
                        "token": self.token,
                        "q": q,
                        "v": v,
                        "above": min_paper_num,
                        "tag": tag,
                    },
                )
            # throw errors when response code != 200.
            if response.status_code == 204:
                return None
            response.raise_for_status()
            tgv = response.json()
            return tgv
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def MclaimThisTask(self, code: str, version: int) -> list:
        """Claim a task from server and get back metadata.

        Args:
            code: a task code such as `"q0123g2"`.
            version: we should know which version we are claiming.

        Returns:
            list: Consisting of image_metadata, [list of tags], integrity_check.

        Raises:
            PlomTakenException: someone got it before you
            PlomRangeException: no such test number or not yet scanned
            PlomVersionMismatchException: the version supplied does not
                match the task's version.
            PlomAuthenticationException:
            PlomSeriousException: generic unexpected error
        """
        with self.SRmutex:
            try:
                if self.is_legacy_server():
                    response = self.patch(
                        f"/MK/tasks/{code}",
                        json={
                            "user": self.user,
                            "token": self.token,
                            "version": version,
                        },
                    )
                else:
                    response = self.patch_auth(f"/MK/tasks/{code}?version={version}")
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                if response.status_code == 409:
                    raise PlomTakenException(response.reason) from None
                if response.status_code == 417:
                    raise PlomVersionMismatchException(response.reason) from None
                if response.status_code == 404:
                    raise PlomRangeException(response.reason) from None
                if response.status_code == 410:
                    raise PlomRangeException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def reassign_task(self, papernum: int, qidx: int, username: str) -> None:
        """Reassign a task that belongs to a user to a different user.

        Some cases to consider:
          - if its TO_DO should we claim it for the user?
          - if it already belongs to that user, is that an error?

        Args:
            papernum: which paper.
            qidx: which question index.
            username: who should we assign it to?

        Returns:
            None.

        Raises:
            PlomRangeException: no such task, or no such user.
            PlomNoPermission: you don't have permission to reassign tasks.
            PlomNoServerSupportException: server too old, does not support.
            PlomAuthenticationException: no logged in.
            PlomSeriousException: generic unexpected error.
        """
        if self.is_server_api_less_than(113):
            raise PlomNoServerSupportException(
                "Server too old: does not support reassign"
            )
        if self.is_server_api_less_than(114):
            code = f"q{papernum:04}g{qidx}"
            url = f"/MK/tasks/{code}/reassign/{username}"
        else:
            url = f"/api/v0/tasks/{papernum}/{qidx}/reassign/{username}"

        with self.SRmutex:
            try:
                response = self.patch_auth(url)
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                if response.status_code == 404:
                    raise PlomRangeException(response.reason) from None
                if response.status_code == 406:
                    raise PlomNoPermission(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def reset_task(self, papernum: int, qidx: int) -> bool:
        """Reset a task, outdating all annotations.

        Args:
            papernum: which paper number.
            qidx: which question index.

        Returns:
            True on success.

        Raises:
            PlomRangeException: no such task
            PlomNoPermission: you don't have permission to reset tasks.
            PlomNoServerSupportException: server too old, does not support.
            PlomAuthenticationException: no logged in.
            PlomSeriousException: generic unexpected error.
        """
        if self.is_server_api_less_than(114):
            raise PlomNoServerSupportException(
                "Server too old: does not support task reset"
            )

        with self.SRmutex:
            try:
                response = self.patch_auth(f"/api/v0/tasks/{papernum}/{qidx}/reset")
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                if response.status_code == 404:
                    raise PlomRangeException(response.reason) from None
                if response.status_code == 406:
                    raise PlomNoPermission(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def MlatexFragment(self, latex: str) -> tuple[bool, bytes | str]:
        """Give some text to the server, it comes back as a PNG image processed via TeX.

        Args:
            latex: a fragment of text including TeX markup.

        Returns:
            `(True, png_bytes)` or `(False, fail_reason)`.
        """
        with self.SRmutex:
            try:
                response = self.post_auth(
                    "/MK/latex",
                    json={"fragment": latex},
                )
                response.raise_for_status()
                image = BytesIO(response.content).getvalue()
                return (True, image)
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                if response.status_code == 406:
                    r = response.json()
                    assert r["error"]
                    return (False, r["tex_output"])
                    # raise PlomLatexException(
                    #     f"Server reported an error processing your TeX fragment:\n\n{response.text}"
                    # ) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def MreturnMarkedTask(
        self,
        code,
        pg,
        ver,
        score,
        marking_time,
        annotated_img,
        plomfile,
        rubrics,
        integrity_check,
    ) -> dict[str, Any]:
        """Upload annotated image and associated data to the server.

        Args:
            code (str): e.g., "q0003g1"
            pg (int): question number.
            ver (int): which version.
            score: assigned score for the task.
            marking_time (int/float): number of seconds spend on grading
                the paper.
            annotated_img (pathlib.Path): the annotated image, either a
                png or a jpeg.
            plomfile (pathlib.Path): machine-readable json of annotations
                on the page.
            rubrics (list): list of rubric IDs used on the page.
            integrity_check (str): a blob that the server expects to get
                back.

        Returns:
            A dict of progress information.  See :meth:`get_marking_progress`.
            There is a a certain aomunt of code duplication to make this
            happen; consider refactoring to avoid needing this to return anything.

        Raises:
            PlomAuthenticationException
            PlomConflict: integrity check failed, perhaps manager
                altered task.
            PlomTimeoutError: network trouble such as timeouts.
            PlomTaskChangedError
            PlomTaskDeletedError
            PlomSeriousException
        """
        if self.is_legacy_server():
            n, m = self._MreturnMarkedTask_legacy(
                code,
                pg,
                ver,
                score,
                marking_time,
                annotated_img,
                plomfile,
                rubrics,
                integrity_check,
            )
            d = {"total_tasks": m, "total_tasks_marked": n, "user_quota_limit": None}
            return d
        return self._MreturnMarkedTask_webplom(
            code, pg, ver, score, marking_time, annotated_img, plomfile, integrity_check
        )

    def _MreturnMarkedTask_legacy(
        self,
        code,
        pg,
        ver,
        score,
        marking_time,
        annotated_img,
        plomfile,
        rubrics,
        integrity_check,
    ):
        # legacy expects the src_img_data duplicated outside of plomfile.
        with open(plomfile, "rb") as f:
            pdict = json.load(f)
        image_md5_list = pdict["base_images"]

        # put the scene in legacy format
        for x in pdict["sceneItems"]:
            if x[0] == "Rubric":
                x[0] = "GroupDeltaText"
                r = x[3]
                log.debug("Rewriting Rubric %d as legacy GroupDeltaText", r["rid"])
                x[3] = r["rid"]
                x.extend(
                    [
                        r["kind"],
                        r["value"],
                        r["out_of"],
                        r["display_delta"],
                        r["text"],
                        r["tags"],
                    ]
                )
                assert len(x) == 10

        orig_plomfile_name = plomfile.name
        with tempfile.TemporaryDirectory() as td:
            hack_pfile = pathlib.Path(td) / plomfile.name
            with open(hack_pfile, "w") as f:
                json.dump(pdict, f, indent="  ")
                f.write("\n")

            img_mime_type = mimetypes.guess_type(annotated_img)[0]
            with self.SRmutex:
                try:
                    with open(annotated_img, "rb") as fh, open(hack_pfile, "rb") as f2:
                        # doesn't like ints, so convert ints to strings
                        param = {
                            "user": self.user,
                            "token": self.token,
                            "pg": str(pg),
                            "ver": str(ver),
                            "score": str(score),
                            "mtime": str(round(marking_time)),
                            "rubrics": rubrics,
                            "md5sum": hashlib.md5(fh.read()).hexdigest(),
                            "integrity_check": integrity_check,
                            "image_md5s": image_md5_list,
                        }
                        # reset stream position to start before reading again
                        fh.seek(0)
                        dat = MultipartEncoder(
                            fields={
                                "param": json.dumps(param),
                                "annotated": (annotated_img.name, fh, img_mime_type),
                                "plom": (orig_plomfile_name, f2, "text/plain"),
                            }
                        )
                        # increase read timeout relative to default: Issue #1575
                        timeout = (self.default_timeout[0], 3 * self.default_timeout[1])
                        response = self.put(
                            f"/MK/tasks/{code}",
                            data=dat,
                            headers={"Content-Type": dat.content_type},
                            timeout=timeout,
                        )
                    response.raise_for_status()
                    return response.json()
                except (requests.ConnectionError, requests.Timeout) as e:
                    raise PlomTimeoutError(
                        "Upload timeout/connect error: {}\n\n".format(e)
                        + "Retries are NOT YET implemented: as a workaround,"
                        + "you can re-open the Annotator on '{}'.\n\n".format(code)
                        + "We will now process any remaining upload queue."
                    ) from None
                except requests.HTTPError as e:
                    if response.status_code == 401:
                        raise PlomAuthenticationException() from None
                    if response.status_code == 406:
                        if response.text == "integrity_fail":
                            raise PlomConflict(
                                "Integrity fail: can happen if manager altered task while you annotated"
                            ) from None
                        raise PlomSeriousException(response.text) from None
                    if response.status_code == 409:
                        raise PlomTaskChangedError(
                            "Task ownership has changed."
                        ) from None
                    if response.status_code == 410:
                        raise PlomTaskDeletedError(
                            "No such task - it has been deleted from server."
                        ) from None
                    if response.status_code == 400:
                        raise PlomSeriousException(response.text) from None
                    raise PlomSeriousException(
                        f"Some other sort of error {e}"
                    ) from None

    def _MreturnMarkedTask_webplom(
        self,
        code,
        pg,
        ver,
        score,
        marking_time,
        annotated_img,
        plomfile,
        integrity_check,
    ):
        """Upload annotated image and data to Django server, using it's built-in multipart data handling.

        See :meth:`MreturnMarkedTask` for docs.
        """
        with self.SRmutex:
            try:
                with (
                    open(annotated_img, "rb") as annot_img_file,
                    open(plomfile, "rb") as plom_data_file,
                ):
                    data = {
                        "pg": str(pg),
                        "ver": str(ver),
                        "score": str(score),
                        "marking_time": marking_time,
                        "md5sum": hashlib.md5(annot_img_file.read()).hexdigest(),
                        "integrity_check": integrity_check,
                    }

                    annot_img_file.seek(0)

                    # automatically puts the filename in
                    files = {
                        "annotation_image": annot_img_file,
                        "plomfile": plom_data_file,
                    }

                    # increase read timeout relative to default: Issue #1575
                    timeout = (self.default_timeout[0], 3 * self.default_timeout[1])
                    response = self.post_auth(
                        f"/MK/tasks/{code}",
                        data=data,
                        files=files,
                        timeout=timeout,
                    )
                    response.raise_for_status()
                    return response.json()
            except (requests.ConnectionError, requests.Timeout) as e:
                raise PlomTimeoutError(
                    "Upload timeout/connect error: {}\n\n".format(e)
                    + "Retries are NOT YET implemented: as a workaround,"
                    + "you can re-open the Annotator on '{}'.\n\n".format(code)
                    + "We will now process any remaining upload queue."
                ) from None
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                if response.status_code == 406:
                    raise PlomConflict(response.reason) from None
                if response.status_code == 409:
                    raise PlomTaskChangedError(response.reason) from None
                if response.status_code == 410:
                    raise PlomTaskDeletedError(response.reason) from None
                if response.status_code == 400:
                    raise PlomSeriousException(response.reason) from None
                if response.status_code == 423:
                    raise PlomQuotaLimitExceeded(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def MgetUserRubricTabs(self, question):
        """Ask server for the user's rubric-tabs config file for this question.

        Args:
            question (int): which question to save to (rubric tabs are
                generally per-question).

        Raises:
            PlomAuthenticationException
            PlomSeriousException

        Returns:
            dict/None: a dict of information about user's tabs for that
            question or `None` if server has no saved tabs for that
            user/question pair.
        """
        self.SRmutex.acquire()
        try:
            response = self.get(
                f"/MK/user/{self.user}/{question}",
                json={
                    "user": self.user,
                    "token": self.token,
                    "question": question,
                },
            )
            response.raise_for_status()

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return None
            else:
                raise PlomSeriousException(
                    "No other 20x response expected from server."
                ) from None

        except requests.HTTPError as e:
            if response.status_code in (401, 403):
                raise PlomSeriousException(response.text) from None
            raise PlomSeriousException(
                f"Error of type {e} when creating new rubric"
            ) from None
        finally:
            self.SRmutex.release()

    def MsaveUserRubricTabs(self, question, tab_config):
        """Cache the user's rubric-tabs config for this question onto the server.

        Args:
            question (int): the current question number
            tab_config (dict): the user's rubric pane configuration for
                this question.

        Raises:
            PlomAuthenticationException
            PlomSeriousException

        Returns:
            None
        """
        self.SRmutex.acquire()
        try:
            response = self.put(
                f"/MK/user/{self.user}/{question}",
                json={
                    "user": self.user,
                    "token": self.token,
                    "question": question,
                    "rubric_config": tab_config,
                },
            )
            response.raise_for_status()

        except requests.HTTPError as e:
            if response.status_code in (401, 403):
                raise PlomSeriousException(response.text) from None
            raise PlomSeriousException(
                f"Error of type {e} when creating new rubric"
            ) from None
        finally:
            self.SRmutex.release()

    def new_server_upload_bundle(self, pdf: Path) -> dict[str, Any]:
        """Upload a PDF file to the server as a new bundle.

        Returns:
            A dictionary, including the bundle_id and maybe other
            information in the future.
        """
        if self.is_server_api_less_than(113):
            raise PlomNoServerSupportException(
                "Server too old: does not support staging bundle upload"
            )

        with self.SRmutex:
            try:
                with pdf.open("rb") as f:
                    files = {
                        "pdf_file": f,
                    }
                    response = self.post_auth("/api/beta/scan/bundles", files=files)
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise PlomSeriousException(response.reason) from None
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 409:
                    raise PlomConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def new_server_list_bundles(self) -> list[list[Any]]:
        """Get a list of information about bundles on the server.

        TODO: beta: rename to something reasonable in due time.

        Returns:
            A list of of lists, representing a table where the first row
            is the column headers.
            TODO: maybe a list of dicts would be a more general API; could
            format as a table client-side.
        """
        if self.is_server_api_less_than(113):
            raise PlomNoServerSupportException(
                "Server too old: does not support staging bundle list"
            )

        with self.SRmutex:
            try:
                response = self.get_auth("/api/beta/scan/bundles")
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def new_server_bundle_map_page(
        self, bundle_id: int, page: int, papernum: int, questions: str | list
    ) -> Any:
        """Map a page of a bundle to zero or more questions.

        TODO: beta: rename to something reasonable in due time.

        Returns:
            TODO: nothing yet, still WIP?
        """
        if self.is_server_api_less_than(113):
            raise PlomNoServerSupportException(
                "Server too old: does not support page mapping"
            )

        with self.SRmutex:
            try:
                # qall TODO?
                # qdnm versus empty list?
                query_args = ["qall", f"papernum={papernum}"]
                print(questions)
                query_args.extend([f"qidx={n}" for n in questions])
                p = (
                    f"/api/beta/scan/bundle/{bundle_id}/{page}/map"
                    + "?"
                    + "&".join(query_args)
                )
                print(p)
                response = self.post_auth(p)
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise PlomSeriousException(response.reason) from None
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 404:
                    raise PlomRangeException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def new_server_push_bundle(self, bundle_id: int):
        """Push a bundle from the staging area.

        TODO: beta: rename to something reasonable in due time.

        Returns:
            TODO: WIP
        """
        if self.is_server_api_less_than(113):
            raise PlomNoServerSupportException(
                "Server too old: does not support bundle push"
            )

        with self.SRmutex:
            try:
                response = self.patch_auth(f"/api/beta/scan/bundle/{bundle_id}")
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise PlomSeriousException(response.reason) from None
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 404:
                    raise PlomNoBundle(response.reason) from None
                if response.status_code == 406:
                    raise PlomConflict(response.reason) from None
                if response.status_code == 409:
                    raise PlomConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def new_server_delete_bundle(self, bundle_id: int):
        """Delete a bundle from the staging area.

        TODO: beta: rename to something reasonable in due time.

        Returns:
            The id of the bundle that was deleted.
        """
        if self.is_server_api_less_than(114):
            raise PlomNoServerSupportException(
                "Server too old: does not support bundle deletion"
            )

        with self.SRmutex:
            try:
                response = self.delete_auth(f"/api/beta/scan/bundle/{bundle_id}")
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise PlomSeriousException(response.reason) from None
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 404:
                    raise PlomNoBundle(response.reason) from None
                if response.status_code == 406:
                    raise PlomConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def new_server_get_reassembled(self, papernum: int) -> dict[str, Any]:
        """Download a reassembled PDF file from the server.

        Returns:
            A dict including key `"filename"` for the file that was written
            and other information about the download.
        """
        if self.is_server_api_less_than(113):
            raise PlomNoServerSupportException(
                "Server too old: API does not support getting reassembled papers"
            )

        with self.SRmutex:
            try:
                response = self.get_auth(
                    f"/api/beta/finish/reassembled/{papernum}", stream=True
                )
                response.raise_for_status()
                # https://stackoverflow.com/questions/31804799/how-to-get-pdf-filename-with-python-requests
                msg = EmailMessage()
                msg["Content-Disposition"] = response.headers.get("Content-Disposition")
                filename = msg.get_filename()
                assert filename is not None
                num_bytes = 0
                # defaults to CWD: TODO: kwarg to change that?
                with open(filename, "wb") as f:
                    for chunk in tqdm(response.iter_content(chunk_size=8192)):
                        print((type(chunk), len(chunk)))
                        f.write(chunk)
                        num_bytes += len(chunk)
                r = {
                    "filename": filename,
                    "content-length": num_bytes,
                }
                return r
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 404:
                    raise PlomNoPaper(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def beta_id_paper(
        self, paper_number: int, student_id: str, student_name: str
    ) -> None:
        """Identify a paper directly, not as part of a IDing task.

        Exceptions:
            PlomConflict: `studentID` already used on a different paper.
            PlomAuthenticationException: login problems.
            PlomSeriousException: other errors.
            PlomNoServerSupportException: old server
        """
        if self.is_server_api_less_than(113):
            raise PlomNoServerSupportException(
                "Server too old: API does not support direct IDing of papers."
            )
        with self.SRmutex:
            try:
                url = f"/ID/beta/{paper_number}"
                url += f"?student_id={student_id}&student_name={student_name}"
                response = self.put_auth(url)
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 404:
                    raise PlomNoPaper(response.reason) from None
                if response.status_code == 409:
                    raise PlomConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def beta_un_id_paper(self, paper_number: int) -> None:
        """Remove the identify of a paper directly.

        Exceptions:
            PlomAuthenticationException: login problems.
            PlomSeriousException: other errors.
        """
        if self.is_server_api_less_than(113):
            raise PlomNoServerSupportException(
                "Server too old: API does not support direct IDing of papers."
            )
        with self.SRmutex:
            try:
                response = self.delete_auth(f"/ID/beta/{paper_number}")
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 404:
                    raise PlomNoPaper(response.reason) from None
                if response.status_code == 406:
                    raise PlomSeriousException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def new_server_upload_spec(self, spec_toml_string: str) -> dict:
        """Upload an assessment spec to the server.

        Args:
            spec_toml_string: The utf-8 string you get by reading a valid spec.toml file

        Exceptions:
            PlomConflict: server already has a database, cannot accept spec.
            ValueError: invalid spec.
            PlomSeriousException: other errors.

        Returns:
            The newly-uploaded spec, as a dict.
        """
        with self.SRmutex:
            try:
                response = self.post_auth(
                    "/api/v0/spec",
                    json={
                        "spec_toml": spec_toml_string,
                    },
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise ValueError(response.reason) from None
                if response.status_code == 403:
                    raise PlomConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

        return response.json()
