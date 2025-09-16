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
        "js": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js",
        "css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css",
        "jsintegrity": "sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI",
        "cssintegrity": "sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB",
        "jsfilename": "bootstrap.bundle.min.js",
        "cssfilename": "bootstrap.min.css",
    },
    {
        "name": "Bootstrap-Icons",
        "license": "MIT",
        "css": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
        "cssfilename": "bootstrap-icons.css",
    },
    {
        "name": "HTMX",
        "license": "0BSD",
        "js": "https://unpkg.com/htmx.org@2.0.6/dist/htmx.js",
        "jsfilename": "htmx.js",
        # "js": "https://unpkg.com/htmx.org@2.0.6/dist/htmx.min.js",
        # "jsfilename": "htmx.min.js",
        "jsintegrity": "sha384-ksKjJrwjL5VxqAkAZAVOPXvMkwAykMaNYegdixAESVr+KqLkKE8XBDoZuwyWVUDv",
    },
    {
        "name": "htmx-ext-response-targets",
        "license": "0BSD",  # ?? probably same as htmx
        "js": "https://cdn.jsdelivr.net/npm/htmx-ext-response-targets@2.0.3/dist/response-targets.js",
        "jsfilename": "response-targets.js",
        # "js": "https://cdn.jsdelivr.net/npm/htmx-ext-response-targets@2.0.3",
        # "jsfilename": "response-targets.min.js",
        "jsintegrity": "sha384-NtTh9TBZ2X/pFpfsVvQOjSsYWmjmqG6h5ioQWVAe2/j3AuTHRmfqvoqp+iOed+I0",
    },
    {
        "name": "Alpine",
        "license": "MIT",
        "js": "https://unpkg.com/alpinejs@3.14.9/dist/cdn.min.js",
        "jsfilename": "alpine.js",
        "jsintegrity": "sha256-PtHu0lJIiSHfZeNj1nFd6wTX+Squ255SGZ/fc8seCtM=",
    },
    {
        "name": "chart.js",
        "license": "MIT",
        "js": "https://cdn.jsdelivr.net/npm/chart.js@4.4.9/dist/chart.umd.js",
        "jsintegrity": "sha256-3jFXc0VLYHa2OZC/oFzlFVo39xmSyH17tfmi6mmGl+8=",
        "jsfilename": "chart.umd.js",
    },
    {
        "name": "d3.js",
        "license": "BSD",
        "js": "https://d3js.org/d3.v6.min.js",
        "jsfilename": "d3.v6.min.js",
    },
    {
        # Sorttable by Stuart Langridge, https://github.com/stuartlangridge/sorttable
        "name": "sorttable",
        "license": "X11",  # https://www.kryogenix.org/code/browser/sorttable/#licence
        # No, blocks direct download:
        # "js": "https://www.kryogenix.org/code/browser/sorttable/sorttable.js",
        "jsintegrity": "sha256-n3657FhpVO0BrpRmnXeQho7yfKvMVBh0QcoYkQr2O8w=",
        "zip": "https://www.kryogenix.org/code/browser/sorttable/sorttable.zip",
        "jsfilename": "sorttable.js",
    },
    {
        # SortableJS (note not Sorttable!) https://github.com/SortableJS/Sortable
        "name": "SortableJS",
        "license": "MIT",
        "js": "https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js",
        "jsintegrity": "sha256-bQqDH8GbS66FF5etM5MVfoYa+3hiRZwRImNZsn4sQzc=",
        "jsfilename": "Sortable.min.js",
    },
    {
        # Unfortunate that we use both "Tablesort" and "sorttable"; they seem similar
        "name": "Tablesort",
        "license": "MIT",
        "js": "https://cdn.jsdelivr.net/npm/tablesort@5.6.0/dist/tablesort.min.js",
        "jsintegrity": "sha256-exTAyB07iPiInEumh/fA2mMNK0dDmoTzRhVoITcKqTA=",
        "jsfilename": "tablesort.min.js",
    },
    {
        "name": "Tablesort.number",
        "license": "MIT",
        "js": "https://cdn.jsdelivr.net/npm/tablesort@5.6.0/dist/sorts/tablesort.number.min.js",
        "jsintegrity": "sha256-RrgkMionKOUBO+Hu+0puHGjKv/GK5FiMUKEIBBt9OzI=",
        "jsfilename": "tablesort.number.min.js",
    },
    {
        # TODO: RC version, no release since Jan 2021, consider replacing
        "name": "select2",
        "license": "MIT",
        "js": "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js",
        "css": "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css",
        "jsfilename": "select2.min.js",
        "cssfilename": "select2.min.css",
    },
    {
        # Used only on the login page (?)
        "name": "mdb-ui-kit",
        "license": "MIT",
        "js": "https://cdnjs.cloudflare.com/ajax/libs/mdb-ui-kit/4.2.0/mdb.min.js",
        "css": "https://cdnjs.cloudflare.com/ajax/libs/mdb-ui-kit/4.2.0/mdb.min.css",
        "jsfilename": "mdb.min.js",
        "cssfilename": "mdb.min.css",
    },
    {
        "name": "JQuery",
        "license": "MIT",
        "js": "https://code.jquery.com/jquery-3.6.4.min.js",
        "jsfilename": "jquery-3.6.4.min.js",
        "jsintegrity": "sha256-oP6HI9z1XaZNBrJURtCoUT5SUnxFr8s3BzRl+cbzUq8=",
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
                "Downloaded sha384 does not match records!\n"
                f"records:  {hash}\n"
                f"download: {sha384}"
            )
        print(f"    {sha384}")
    else:
        if hash != sha256:
            raise ValueError(
                "Downloaded sha256 does not match records!\n"
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

    Path(destdir).mkdir(exist_ok=True)
    static_js.mkdir(exist_ok=True)
    static_css.mkdir(exist_ok=True)
    print("Checking/downloading vendored JavaScript and CSS:")
    for row in table:
        if row.get("zip"):
            # special case for zip
            check_or_download_and_unzip(
                static_js, row["jsfilename"], row["zip"], row.get("jsintegrity")
            )
            continue
        if row.get("js"):
            check_or_download_file(
                row["js"], static_js, row["jsfilename"], hash=row.get("jsintegrity")
            )
        if row.get("css"):
            check_or_download_file(
                row["css"], static_css, row["cssfilename"], hash=row.get("cssintegrity")
            )


if __name__ == "__main__":
    download_javascript_and_css_to_static()
