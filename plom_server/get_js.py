# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

import re
from pathlib import Path

import requests

# Javascript/CSS 3rd-party-library downloader
# ===========================================
#
# This is not yet used for anything (Issue #2763) but it does try
# to be a WET table of all our JS/CSS libraries (Issue #2762).
#
# FAQ: why not learn `npm` or something?  Yes please help.
#
# Maintenance
# -----------
#
# In many cases, the html file would also list the integrity.
# That needs to be manually updated.  Actually why bother if local,
# we could just check here...?

table = [
    {
        "what": "Bootstrap",
        "license": "MIT",
        "css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
        "js": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
        "integrity": "sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz",
    },
    {
        "what": "Bootstrap-Icons",
        "license": "MIT",
        "css": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
    },
    {
        "what": "HTMX",
        "license": "0BSD",
        "js": "https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js",
    },
    {
        "what": "Alpine",
        "license": "MIT",
        "js": "https://unpkg.com/alpinejs@3.14.8/dist/cdn.min.js",
        "js-filename": "apline.js",
    },
    {
        "what": "chart.js",
        "license": "MIT",
        "js": "https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.js",
        "integrity": "sha256-5M9NFEsiJjTy5k/3B81XuVP43ktlsjHNWsa94RRkjk0=",
    },
    {
        "what": "d3.js",
        "license": "BSD",
        "js": "https://d3js.org/d3.v6.min.js",
    },
    {
        # Sorttable by Stuart Langridge, https://github.com/stuartlangridge/sorttable
        "what": "Sorttable",
        "license": "X11",  # https://github.com/stuartlangridge/sorttable/blob/master/sorttable/sorttable.js
        "js": "https://www.kryogenix.org/code/browser/sorttable/sorttable.js",
    },
    {
        "what": "select2",
        "license": "MIT",
        "js": "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js",
        "css": "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css",
    },
    {
        # Used only on the login page (?)
        "what": "mdb-ui-kit",
        "license": "TODO",
        "js": "https://cdnjs.cloudflare.com/ajax/libs/mdb-ui-kit/4.2.0/mdb.min.js",
        "css": "https://cdnjs.cloudflare.com/ajax/libs/mdb-ui-kit/4.2.0/mdb.min.css",
    },
    {
        "what": "JQuery",
        "license": "TODO",
        "js": "https://code.jquery.com/jquery-3.6.0.min.js",
    },
]


def download_file(url: str, save_to: Path, *, filename: str | None = None) -> None:
    r = requests.get(url)

    if filename is None:
        if "Content-Disposition" in r.headers.keys():
            filename = re.findall("filename=(.+)", r.headers["Content-Disposition"])[0]
        else:
            filename = url.split("/")[-1]

    with open(save_to / filename, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            f.write(chunk)


if __name__ == "__main__":
    static_js = Path("static/3rdpartyjs")
    static_css = Path("static/3rdpartycss")
    static_js.mkdir(exist_ok=True)
    static_css.mkdir(exist_ok=True)
    for row in table:
        print(row["what"])
        if row.get("js"):
            download_file(row["js"], static_js, filename=row.get("js-filename"))
            # TODO: verify integrity if present
        if row.get("css"):
            download_file(row["css"], static_css)
