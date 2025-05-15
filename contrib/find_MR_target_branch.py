#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Aidan Murphy

"""Find gitlab repository branch[es] as the predicted MR target for given commits.

Inputs specify a git commit within a particular repository. First check for
existing MRs with this commit as the HEAD of the source branch; if none exist,
return a default.
Output is of the form `<repository_name> <branch>` for each target branch found.

Requires glab and git to be installed
"""

import argparse
import subprocess
import json
import sys

REMOTE_NAME = "upstream"


def _get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="\n".join(__doc__.split("\n")[1:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-s",
        "--source",
        type=str,
        help="Search for MRs using this source branch.",
    )

    parser.add_argument(
        "-r",
        "--repo",
        type=str,
        help="The repo to search for MRs.",
    )

    parser.add_argument(
        "--default",
        type=str,
        help="The output if no MRs can be found.",
        default="origin main",
    )

    return parser


def find_gitlab_MR_targets(repo, source_branch) -> list[str]:
    # https://stackoverflow.com/questions/4514751/pipe-subprocess-standard-output-to-a-variable
    proc = subprocess.Popen(
        [
            "glab",
            "mr",
            "list",
            f"--source-branch={source_branch}",
            f"--repo={repo}",
            "--output",
            "json",
        ],
        stdout=subprocess.PIPE,
    )
    json_string = proc.stdout.read().decode("utf8")
    mr_list = json.loads(json_string)

    return [mr_dict["target_branch"] for mr_dict in mr_list]


def main():
    parser = _get_parser()
    args = parser.parse_args()

    # empty strings should output the default value,
    # use an illegal branch name to return 0 target branches.
    if args.source == "":
        args.source = " _"

    if not (args.repo and args.source):
        parser.print_help()
        sys.exit(1)

    branch_list = find_gitlab_MR_targets(args.repo, args.source)
    if len(branch_list) > 0:
        upstream_branch_list = "\n".join([REMOTE_NAME + " " + s for s in branch_list])
        print(upstream_branch_list)
    else:
        print(args.default)


if __name__ == "__main__":
    main()
