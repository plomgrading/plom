# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

import hashlib
import re
import shutil
import tempfile
from base64 import b64encode
from pathlib import Path

import requests

# Javascript/CSS 3rd-party-library downloader
# ===========================================
#
# This downloads our Javascript and CSS dependencies for local static
# caching.
#
# FAQ: why not learn `npm` or something?  Yes please help.
#
# Maintenance
# -----------
#
# Bump these sometimes!

table = [
    {
        "name": "Bootstrap-js",
        "license": "MIT",
        "files": [
            {
                "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js",
                "hash": "sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI",
            },
            {
                "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js.map",
                "hash": "sha256-xhEj5YzApLZdc3ugcMSFkRs9vsbXuAK99mKDlavZwIs=",
            },
            {
                "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css",
                "hash": "sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB",
            },
            {
                "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css.map",
                "hash": "sha256-SBRPr2qg+zzSznSNlzAjj4iPSrcV8F2r0cmvLFZxmIo=",
            },
        ],
    },
    {
        "name": "Bootstrap-Icons",
        "license": "MIT",
        "files": [
            {
                "url": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.css",
                "hash": "sha256-AEMichyFVzMXWbxt2qy7aJsPBxXWiK7IK9BW0tW1zDs=",
            },
            {
                "url": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/fonts/bootstrap-icons.woff",
                "hash": "sha256-9VUTt7WRy4SjuH/w406iTUgx1v7cIuVLkRymS1tUShU=",
            },
            {
                "url": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/fonts/bootstrap-icons.woff2",
                "hash": "sha256-bHVxA2ShylYEJncW9tKJl7JjGf2weM8R4LQqtm/y6mE=",
            },
        ],
    },
    {
        "name": "HTMX",
        "license": "0BSD",
        "files": [
            {
                "url": "https://unpkg.com/htmx.org@2.0.7/dist/htmx.js",
                "hash": "sha256-OkbJL4z95vvR20hS8JSzBBiOUsgGmk8vejf0kQirF3U=",
            },
        ],
    },
    {
        "name": "htmx-ext-response-targets",
        "license": "0BSD",  # ?? probably same as htmx
        "files": [
            {
                "url": "https://cdn.jsdelivr.net/npm/htmx-ext-response-targets@2.0.3/dist/response-targets.js",
                "hash": "sha384-NtTh9TBZ2X/pFpfsVvQOjSsYWmjmqG6h5ioQWVAe2/j3AuTHRmfqvoqp+iOed+I0",
            },
        ],
    },
    {
        "name": "Alpine",
        "license": "MIT",
        "files": [
            {
                "url": "https://unpkg.com/alpinejs@3.15.0/dist/cdn.min.js",
                "filename": "alpine.js",
                "hash": "sha256-4EHxtjnR5rL8JzbY12OKQJr81ESm7JBEb49ORPo29AY=",
            },
        ],
    },
    {
        "name": "chart.js",
        "license": "MIT",
        "files": [
            {
                "url": "https://cdn.jsdelivr.net/npm/chart.js@4.4.9/dist/chart.umd.js",
                "hash": "sha256-3jFXc0VLYHa2OZC/oFzlFVo39xmSyH17tfmi6mmGl+8=",
            },
        ],
    },
    {
        # Sorttable by Stuart Langridge, https://github.com/stuartlangridge/sorttable
        "name": "sorttable",
        "license": "X11",  # https://www.kryogenix.org/code/browser/sorttable/#licence
        # No, blocks direct download:
        # "url": "https://www.kryogenix.org/code/browser/sorttable/sorttable.js",
        "hash": "sha256-n3657FhpVO0BrpRmnXeQho7yfKvMVBh0QcoYkQr2O8w=",
        "zip": "https://www.kryogenix.org/code/browser/sorttable/sorttable.zip",
        "filename": "sorttable.js",
    },
    {
        # SortableJS (note not Sorttable!) https://github.com/SortableJS/Sortable
        "name": "SortableJS",
        "license": "MIT",
        "files": [
            {
                "url": "https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js",
                "hash": "sha256-bQqDH8GbS66FF5etM5MVfoYa+3hiRZwRImNZsn4sQzc=",
            }
        ],
    },
    {
        # Unfortunate that we use both "Tablesort" and "sorttable"; they seem similar
        "name": "Tablesort",
        "license": "MIT",
        "files": [
            {
                "url": "https://cdn.jsdelivr.net/npm/tablesort@5.6.0/dist/tablesort.min.js",
                "hash": "sha256-exTAyB07iPiInEumh/fA2mMNK0dDmoTzRhVoITcKqTA=",
            },
            {
                "url": "https://cdn.jsdelivr.net/npm/tablesort@5.6.0/dist/sorts/tablesort.number.min.js",
                "hash": "sha256-RrgkMionKOUBO+Hu+0puHGjKv/GK5FiMUKEIBBt9OzI=",
            },
        ],
    },
    {
        # TODO: RC version, no release since Jan 2021, consider replacing
        "name": "select2",
        "license": "MIT",
        "files": [
            {
                "url": "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js",
                "hash": "sha256-9yRP/2EFlblE92vzCA10469Ctd0jT48HnmmMw5rJZrA=",
            },
            {
                "url": "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css",
                "hash": "sha256-zaSoHBhwFdle0scfGEFUCwggPN7F+ip9XRglo8IWb4w=",
            },
        ],
    },
    {
        # Used only on the login page (?)
        "name": "mdb-ui-kit",
        "license": "MIT",
        "files": [
            {
                "url": "https://cdnjs.cloudflare.com/ajax/libs/mdb-ui-kit/4.2.0/mdb.min.js",
                "hash": "sha256-y+Pa+MbXsX6NG/fYpJV07UA0o5KW9YaP+YvNoZNTapI=",
            },
            {
                "url": "https://cdnjs.cloudflare.com/ajax/libs/mdb-ui-kit/4.2.0/mdb.min.css",
                "hash": "sha256-dqc3ralMj9oruQZRUoBCEJqXVmvrulSKRxBIzaJVwpY=",
            },
        ],
    },
    {
        "name": "JQuery",
        "license": "MIT",
        "files": [
            {
                "url": "https://code.jquery.com/jquery-3.6.4.min.js",
                "hash": "sha256-oP6HI9z1XaZNBrJURtCoUT5SUnxFr8s3BzRl+cbzUq8=",
            },
        ],
    },
]


def download_file(url: str, save_to: Path, *, filename: str | None = None) -> None:
    """Download a file from a URL."""
    r = requests.get(url)
    if filename is None:
        if "Content-Disposition" in r.headers.keys():
            filename = re.findall("filename=(.+)", r.headers["Content-Disposition"])[0]
        else:
            filename = url.split("/")[-1]
    with open(save_to / filename, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            f.write(chunk)


def check_or_download_file(
    url: str, save_to: Path, filename: str, *, hash: str | None = None
) -> None:
    """Download if not present, then check file hash."""
    f = save_to / filename
    if f.exists():
        print(f" *  {f}")
    else:
        print(f"Downloading {f}...")
        download_file(url, save_to, filename=filename)
    check_file(f, hash=hash)


def check_or_download_and_unzip(save_to, filename, zipurl, hash):
    """If file exists, check if hash, else download it by downloading and unpacking a zip."""
    f = save_to / filename
    if f.exists():
        print(f" *  {f}")
    else:
        print(f"Downloading {f}...")
        with tempfile.TemporaryDirectory() as _td:
            td = Path(_td)
            download_file(zipurl, td, filename="meh.zip")
            shutil.unpack_archive(td / "meh.zip", td)
            shutil.copy(td / filename, save_to)
    check_file(f, hash=hash)


def check_file(f, hash: str | None = None):
    """Check if a file matches a hash and echo info to stdout."""
    with f.open("rb") as fh:
        c = fh.read()
        sha256 = "sha256-" + b64encode(hashlib.sha256(c).digest()).decode("utf-8")
        sha384 = "sha384-" + b64encode(hashlib.sha384(c).digest()).decode("utf-8")
    if hash is None:
        print(f"    {sha256}")
    elif hash.startswith("sha384-"):
        if hash != sha384:
            raise ValueError(
                f"Downloaded sha384 for {f} does not match records!\n"
                f"records:  {hash}\n"
                f"download: {sha384}"
            )
        print(f"    {sha384}")
    else:
        if hash != sha256:
            raise ValueError(
                f"Downloaded sha256 for {f} does not match records!\n"
                f"records:  {hash}\n"
                f"download: {sha256}\n"
            )
        print(f"    {sha256}")


def download_javascript_and_css_to_static(destdir: None | str = None):
    """Download javascript to for static caching."""
    if destdir is None:
        # Note: defaults to same dir mentioned in plom_server/settings.py
        destdir = "plom_extra_static"
    static_js = Path(destdir) / "js3rdparty"
    static_css = Path(destdir) / "css3rdparty"
    static_css_fonts = Path(destdir) / "css3rdparty/fonts"

    Path(destdir).mkdir(exist_ok=True)
    static_js.mkdir(exist_ok=True)
    static_css.mkdir(exist_ok=True)
    static_css_fonts.mkdir(exist_ok=True)
    print("Checking/downloading vendored JavaScript and CSS:")
    for row in table:
        assert isinstance(row, dict)
        if row.get("files"):
            for f in row["files"]:
                filename = f.get("filename")
                if not filename:
                    filename = f["url"].split("/")[-1]
                fcf = filename.casefold()
                if fcf.endswith(".js"):
                    where = static_js
                elif fcf.endswith(".js.map"):
                    where = static_js
                elif fcf.endswith(".css"):
                    where = static_css
                elif fcf.endswith(".css.map"):
                    where = static_css
                elif fcf.endswith(".woff") or fcf.endswith(".woff2"):
                    where = static_css_fonts
                else:
                    raise RuntimeError(f"unexpected filetype: {f}")
                check_or_download_file(f["url"], where, filename, hash=f.get("hash"))
        elif row.get("zip"):
            # special case for zip
            check_or_download_and_unzip(
                static_js, row["filename"], row["zip"], row.get("hash")
            )
        else:
            raise RuntimeError(f"unexpected format in row {row}")


if __name__ == "__main__":
    download_javascript_and_css_to_static()
