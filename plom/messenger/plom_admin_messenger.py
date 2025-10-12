# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2025 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen
# Copyright (C) 2025 Aidan Murphy

"""Extended bits 'n bobs for advanced non-stable features of Plom server."""

import logging
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import requests

from plom.plom_exceptions import (
    PlomAuthenticationException,
    PlomConflict,
    PlomDependencyConflict,
    PlomNoBundle,
    PlomNoPaper,
    PlomNoPermission,
    PlomNoServerSupportException,
    PlomRangeException,
    PlomSeriousException,
    PlomVersionMismatchException,
)
from .messenger import Messenger


log = logging.getLogger("messenger")


class PlomAdminMessenger(Messenger):
    """Extend the Messenger to handle more advanced communication with a Plom Server."""

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
                    files = {"pdf_file": f}
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
        self,
        bundle_id: int,
        page: int,
        *,
        papernum: int | None = None,
        questions: int | str | list[int | str],
    ) -> None:
        """Map the indicated page of the specified bundle to all questions in a list, etc.

        TODO: beta: rename to something reasonable in due time.

        Args:
            bundle_id: the (unstaged) bundle's primary key, an integer
            page: the 1-based index of the page of interest in that bundle

        Keyword Args:
            papernum: the target paper number for this page.  If discarding, you
                may omit this.
            questions: A list of question(s) to which this page should be attached.
                Each list entry can be either an integer question index
                compatible with the assessment spec, or one of the special strings
                "all", "dnm", or "discard". Lists that contain any one of these strings
                must have no other elements (i.e., they must be lists of length 1).
                If this argument is a single int or a single string, that will be
                upgraded to a compatible 1-element list and treated appropriately.
                The empty list will be interpreted as ["all"].

        Raises:
            PlomSeriousException
            PlomAuthenticationException
            PlomNoPermission
            PlomRangeException
            PlomSeriousException
            ValueError: malformed input that we detected before communication.

        Returns:
            None
        """
        if self.is_server_api_less_than(113):
            raise PlomNoServerSupportException(
                "Server too old: does not support page mapping"
            )

        query_args = []
        if papernum is not None:
            query_args.append(f"papernum={papernum}")

        if isinstance(questions, str) or isinstance(questions, int):
            questions = [questions]

        if any(isinstance(n, str) for n in questions):
            lc_questions = [
                n.casefold() if isinstance(n, str) else n for n in questions
            ]

            if len(lc_questions) > 1:
                if (
                    "all" in lc_questions
                    or "dnm" in lc_questions
                    or "discard" in lc_questions
                ):
                    raise ValueError(
                        "Mapping error in Messenger: keyword directives must be isolated."
                    )
            if "all" in lc_questions:
                query_args.append("page_dest=all")
            elif "dnm" in lc_questions:
                query_args.append("page_dest=dnm")
            elif "discard" in lc_questions:
                query_args.append("page_dest=discard")
            elif all(isinstance(n, int) or n.isdecimal() for n in questions):
                query_args.extend([f"qidx={n}" for n in questions])
            else:
                raise ValueError(f"unexpected input: questions={questions}")
        else:
            if len(questions) == 0:
                query_args.append("page_dest=all")
            else:
                query_args.extend([f"qidx={n}" for n in questions])

        p = f"/api/beta/scan/bundle/{bundle_id}/{page}/map" + "?" + "&".join(query_args)
        with self.SRmutex:
            try:
                response = self.post_auth(p)
                response.raise_for_status()
                return
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

    def new_server_push_bundle(self, bundle_id: int) -> dict[str, Any]:
        """Push a bundle from the staging area.

        TODO: beta: rename to something reasonable in due time.

        Returns:
            A dictionary, with sole key "bundle_id" mapping to int,
            and maybe other information in the future.
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

    def new_server_get_paper_marks(self) -> dict[int, dict]:
        """Get a list of information about exam papers on the server.

        More specifically this contains info about student marks and IDs.

        Returns:
            A dict of information keyed by the paper number it corresponds to.
        """
        if self.is_server_api_less_than(113):
            raise PlomNoServerSupportException(
                "Server too old: does not support getting plom marks"
            )

        with self.SRmutex:
            try:
                response = self.get_auth("/REP/spreadsheet")
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def new_server_get_unmarked(self, papernum: int, memfile=None):
        """Download an unmarked PDF file from the Plom server.

        Args:
            papernum: the paper number of the paper to fetch.
            memfile: a reference to a NamedTemporaryFile. It must be
                opened with write permissions in **byte** mode.
                If unprovided, one will be created. **The caller
                must close this file**.

        Returns:
            A reference to the NamedTemporaryFile passed in. It should now
            contain the reassembled exam paper specified by papernum.
        """
        if self.is_server_api_less_than(114):
            raise PlomNoServerSupportException(
                "Server too old: API does not support getting unmarked papers"
            )

        with self.SRmutex:
            try:
                response = self.get_auth(
                    f"/api/beta/finish/unmarked/{papernum}", stream=True
                )
                response.raise_for_status()
                # https://stackoverflow.com/questions/31804799/how-to-get-pdf-filename-with-python-requests
                msg = EmailMessage()
                msg["Content-Disposition"] = response.headers.get("Content-Disposition")
                filename = msg.get_filename()
                assert filename is not None

                if memfile is None:
                    memfile = NamedTemporaryFile("wb+")

                memfile.name = filename
                for chunk in response.iter_content(chunk_size=8192):
                    memfile.write(chunk)
                memfile.seek(0)  # be kind, and rewind

            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 404:
                    raise PlomNoPaper(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

            return memfile

    def new_server_get_reassembled(self, papernum: int, memfile=None):
        """Download a reassembled PDF file from the Plom server.

        Args:
            papernum: the paper number of the paper to fetch.
            memfile: a reference to a NamedTemporaryFile. It must be
                opened with write permissions in **byte** mode.
                If unprovided, one will be created. **The caller
                must close this file**.

        Returns:
            A reference to the NamedTemporaryFile passed in. It should now
            contain the reassembled exam paper specified by papernum.
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

                if memfile is None:
                    memfile = NamedTemporaryFile("wb+")

                memfile.name = filename
                for chunk in response.iter_content(chunk_size=8192):
                    memfile.write(chunk)
                memfile.seek(0)  # be kind, and rewind

            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 404:
                    raise PlomNoPaper(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

            return memfile

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

    def new_server_upload_source(
        self, version: int, source_pdf: Path
    ) -> dict[str, Any]:
        """Upload an assessment source to the server.

        Args:
            version: The source version number. Must be compatible with the spec.
            source_pdf: The path to a valid source file.
                (Passing an empty file will vacate the corresponding source slot.)

        Exceptions:
            PlomAuthenticationException: user not logged in, or not in manager group
            PlomDependencyConflict: server state is incompatible with changes to a source.
            PlomVersionMismatchException: source number out of range set by spec
            PlomSeriousException: other errors.

        Returns:
            The dict produced by SourceService, as documented elsewhere.
            ("version": int, "uploaded": bool, "hash": str)
        """
        with self.SRmutex:
            try:
                with source_pdf.open("rb") as f:
                    files = {"source_pdf": f}
                    response = self.post_auth(
                        f"/api/v0/source/{version:d}", files=files
                    )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise PlomVersionMismatchException(response.reason) from None
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 404:
                    raise PlomSeriousException(response.reason) from None
                if response.status_code == 409:
                    raise PlomDependencyConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

        return response.json()

    def new_server_delete_source(self, version: int) -> dict[str, Any]:
        """Delete the specified assessment source from the server.

        Args:
            version: The source version number. Must be compatible with the spec.

        Exceptions:
            PlomAuthenticationException: user not logged in, or not in manager group
            PlomDependencyConflict: server state is incompatible with changes to a source.
            PlomVersionMismatchException: source number out of range set by spec
            PlomSeriousException: other errors.

        Returns:
            The updated list of dicts, one for each source expected by the spec,
            describing the status of the sources in the database. Typically,
            {"version": int, "uploaded": bool, "hash": str}
        """
        with self.SRmutex:
            try:
                response = self.delete_auth(f"/api/v0/source/{version:d}")
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise PlomVersionMismatchException(response.reason) from None
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 404:
                    raise PlomSeriousException(response.reason) from None
                if response.status_code == 409:
                    raise PlomDependencyConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

        return response.json()

    def new_server_upload_spec(
        self, spec_toml: Path, *, force_public_code: bool = False
    ) -> dict[str, Any]:
        """Upload an assessment spec to the server.

        Args:
            spec_toml: The standard Python Path of a valid spec.toml file

        Keyword Args:
            force_public_code: Usually you may not include "publicCode" in
                the specification.  Pass True to allow overriding that default.

        Returns:
            The newly-uploaded spec, as a dict.

        Exceptions:
            PlomConflict: server already has a database, cannot accept spec.
            PlomNoPermission: user is not in the group required to make
                these changes.
            ValueError: invalid spec.
            PlomSeriousException: other errors unexpected errors.
        """
        # Caution: don't use json= with post when files= is used: use data= instead
        # https://requests.readthedocs.io/en/latest/user/quickstart/#more-complicated-post-requests
        if force_public_code:
            data = {"force_public_code": "on"}
        else:
            data = {}

        with self.SRmutex:
            try:
                with spec_toml.open("rb") as f:
                    response = self.post_auth(
                        "/api/v0/spec",
                        files={"spec_toml": f},
                        data=data,
                    )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise ValueError(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 409:
                    raise PlomConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

        return response.json()

    def new_server_delete_classlist(self) -> None:
        """Delete the classlist (if any) held by the server."""
        with self.SRmutex:
            try:
                response = self.delete_auth("/api/v0/classlist")
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 409:
                    raise PlomConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def new_server_download_classlist(self) -> BytesIO:
        """Download the classlist (if any) held by the server.

        Returns:
            BytesIO object with the classlist in standard form, i.e.,
            one header row followed by rows of student data.

        Raises:
            PlomSeriousException - if the GET request produces an HTTPError
        """
        with self.SRmutex:
            try:
                response = self.get_auth("/api/v0/classlist", stream=True)
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

        csv_content = BytesIO(response.content)

        return csv_content

    def new_server_upload_classlist(
        self, csvpath: Path
    ) -> tuple[bool, list[dict[str, Any]]]:
        """Use the given CSV file to extend the classlist on the server.

        Typically the server classlist starts empty and this is used just once.
        Alternatively, it will add new students to a nonempty classlist.
        But the extension must be strict: if the upload mentions a student ID
        or a paper number that is already known to the server,
        the whole upload gets cancelled and the server classlist stays as-is.

        Returns:
            2-tuple of (success,werr), with success boolean and werr a list
            of dicts, each entry providing details on an error or warning.
            It's possible for werr to contain interesting reading even when
            success==True. Dealing with those messages is the caller's job.

        Raises:
            PlomConflict: error with the classlist.
            PlomAuthenticationException: not authenticated.
            PlomNoPermission: you don't have permission to upload classlists.
            PlomSeriousException: unexpected errors.
        """
        with self.SRmutex:
            try:
                with csvpath.open("rb") as f:
                    filedict = {"classlist_csv": f}
                    response = self.patch_auth("/api/v0/classlist", files=filedict)
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise PlomConflict(
                        f"Classlist upload failed: {response.reason}"
                    ) from None
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 406:
                    raise PlomConflict(
                        f"Classlist upload failed: {response.json()}"
                    ) from None
                raise PlomSeriousException(
                    f"Classlist upload failed: error {e}"
                ) from None

        werr = response.json()
        return True, werr

    def rectangle_extraction(
        self, version: int, page_num: int, paper_num: int, region: dict[str, float]
    ) -> bytes:
        """Download the extracted region of the paper with the given version and page number.

        Args:
            version: the version of the page to be extracted
            page_num: the page_num to be extracted.
            paper_num: the paper_num to be extracted.
            region: the boundaries of the rectangle, containing these
                keys: ["left", "right", "top", "bottom"].

        Returns:
            The PNG bytes of the extracted rectangle returned by the server.
        """
        with self.SRmutex:
            try:
                response = self.get_auth(
                    f"/api/rectangle/{version}/{page_num}/{paper_num}", params=region
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                raise PlomSeriousException(f"Some other sort of error {e}") from None

        return response.content
