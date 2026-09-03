#!/usr/bin/env -S python3 -u

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi
# Copyright (C) 2021-2026 Colin B. Macdonald
# Copyright (C) 2022 Nicholas J H Lai
# Copyright (C) 2023 Laurent Mackay
# Copyright (C) 2025-2026 Aidan Murphy

r"""Upload papers and grades to Brightspace from Plom.

Overview:

  1. Finish grading
  2. Reassemble papers.
  3. Copy this script into the current directory, and install:
    - tqdm
    - brightspace-api
    - exif
    - plom-common
    - tabulate
    - python-dotenv (optional)
  4. Run this script and follow the interactive menus:
     ```
     ./plom-push-to-brightspace-uncached.py --dry-run
     ```
     It will output what would be uploaded.
     Note that you can provide command line arguments and/or
     set environment variables to avoid the interactive prompts:
     ```
     ./plom-push-to-brightspace-uncached.py --help
     ```
  5. Run it again for real:
     ```
     ./plom-push-to-brightspace-uncached.py --org-id xxxxxx \
                            --folder-id xxxxxx \
                            --plom-server xxxxxx \
                            --plom-username xxxxx \
                            --no-section 2>&1 | tee push.log
     ```

This script traverses all identified and marked papers in your Plom
server. It will ignore exams that are unidentified and/or unmarked.
"""

import argparse
import os
import random
import string
import sys
import time
from getpass import getpass
from pathlib import Path
from typing import Any

from tqdm import tqdm
from tabulate import tabulate

import bsapi

from plom.cli import start_messenger
from plom.common.exceptions import PlomException

__DEFAULT_BRIGHTSPACE_API_URL__ = "ubc.brightspace.com"
ENTITY_TYPE = "user"  # "user" or "group"
FEEDBACK_TEXT = "Please see attached files(s)."

# These are the keys for the json returned by the Plom 'get spreadsheet' API call
PLOM_STUDENT_ID = "StudentID"
PLOM_STUDENT_NAME = "StudentName"
PLOM_MARKS = "Total"
PLOM_PAPERNUM = "PaperNumber"
PLOM_WARNINGS = "warnings"


CHECKMARK = "\u2713"
CROSS = "\u274c"


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="\n".join(__doc__.split("\n")[1:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=__DEFAULT_BRIGHTSPACE_API_URL__,
        action="store",
        help=f'URL for talking to Brightspace, defaults to "{__DEFAULT_BRIGHTSPACE_API_URL__}".',
    )
    parser.add_argument(
        "--api-key",
        type=str,
        action="store",
        help="""
            The access token for talking to Brightspace.
        """,
    )
    parser.add_argument(
        "--org-id",
        type=int,
        action="store",
        help="""
            The Brightspace org (usually a course) to upload to.
        """,
    )
    parser.add_argument(
        "--folder-id",
        type=int,
        action="store",
        help="""
            The Brightspace folder (usually an assignment) to upload to.
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry-run without writing grades or uploading files to Brightspace.",
    )

    parser.add_argument(
        "--no-papers",
        dest="papers",
        action="store_false",
        help="""
            Don't push the reassembled papers.
        """,
    )
    parser.add_argument(
        "--solutions",
        action="store_true",
        default=False,
        help="""
            Upload individualized solutions, in addition to reassembled papers
            (default: off).
        """,
    )
    parser.add_argument(
        "--reports",
        action="store_true",
        default=False,
        help="""
            Upload individualized student reports, in addition to reassembled papers
            (default: off).
        """,
    )

    parser.add_argument(
        "-s",
        "--plom-server",
        metavar="SERVER[:PORT]",
        help="""
            URL of server to contact. In SERVER, the protocol prefix is semi-optional:
            you can omit it and get https by default, or you can force http by including
            that explicitly.
            The environment variable PLOM_SERVER will be used if --plom-server is not given.
        """,
    )
    parser.add_argument(
        "-u",
        "--plom-username",
        type=str,
        help="""
            Also checks the environment variable PLOM_USERNAME.
        """,
    )
    parser.add_argument(
        "-w",
        "--plom-password",
        type=str,
        help="""
            Also checks the environment variable PLOM_PASSWORD.
        """,
    )

    return parser


def get_interactively_from_dict(choices: dict, *, prompt="Select one:"):
    """Ask user to pick a key, return the value."""
    print(f"\n{prompt}")
    print("  --------------------------------------------------------------------")

    for i, key in enumerate(choices.keys()):
        print(f"    {i}: {key}")

    key_chosen = False
    while not key_chosen:
        user_input = input("\n  Enter [0-n]: ")
        if not (set(user_input) <= set(string.digits)):
            print("Please respond with a nonnegative integer.")
        elif int(user_input) >= len(choices.keys()):
            print("Choice too large.")
        else:
            user_input = int(user_input)
            print(
                "  --------------------------------------------------------------------"
            )
            selection = list(choices.keys())[user_input]
            print(f"  You selected {user_input}: {selection}")
            confirmation = input("  Confirm choice? [Y/n] ")
            if confirmation in ["", "\n", "y", "Y"]:
                key_chosen = True

    return choices[selection]


###########################################################
# A suite of functions to get Brightspace related stuff
def get_courses_teaching(api: bsapi.BSAPI) -> list[tuple[int, str]]:
    """Get a list of the Brightspace courses a particular user is teaching.

    Args:
        api: the Brightspace API instance to check.

    Returns:
        A list of tuples, the first item is the org id, the second is the org name.
    """
    courses_teaching = []
    for course in api.get_course_enrollments():
        # observed types are "Learner", "TA"
        if course.access.classlist_role_name not in ["TA"]:
            continue
        courses_teaching.append((course.org_unit.id, course.org_unit.name))

    return courses_teaching


def interactively_get_org(api) -> tuple[int, str]:
    """Interactively get an org from a brightspace api instance.

    CAUTION: this assumes each org is uniquely named.
    Duplicates are discarded.

    Args:
        api: the Brightspace api instance

    Returns:
        A tuple containing the org id and name.
    """
    course_name_id_dict = {
        cname: (cid, cname) for cid, cname in get_courses_teaching(api)
    }
    org_id, org_name = get_interactively_from_dict(
        course_name_id_dict, prompt="Available orgs:"
    )
    print(f'  Note: you can use "--org-id {org_id}" to reselect.\n\n')
    return org_id, org_name


def get_assignments(api: bsapi.BSAPI, org_id: int) -> list[tuple[int, str]]:
    """Get a list of assignments for a given org.

    Args:
        api: The Brightspace api instance.
        org_id: The org id as an integer .

    Returns:
        A list of tuples; each tuple contains the folder ID and folder name
        for the assignment dropbox.
    """
    folders = api.get_dropbox_folders(org_id)
    assignment_list = []
    for folder in folders:
        assignment_list.append((folder.id, folder.name))
    return assignment_list


def interactively_get_folder(api: bsapi.BSAPI, org_id: int) -> tuple[int, str]:
    """Interactively get an assignment folder from a given course.

    CAUTION: this assumes each assignment folder is uniquely named.
    Duplicates are discarded.

    Args:
        api: The Brightspace api instance.
        org_id: The org id as an integer .

    Returns:
        A tuple containing the folder id and name.
    """
    assignment_name_id_dict = {
        aname: (aid, aname) for aid, aname in get_assignments(api, org_id)
    }
    folder_id, folder_name = get_interactively_from_dict(
        assignment_name_id_dict, prompt="Available folders:"
    )
    print(f'  Note: you can use "--folder-id {folder_id}" to reselect.\n\n')
    return folder_id, folder_name


def get_brightspace_learner_id_dict(api, org_id) -> dict[str, int]:
    """Get a dict of brightspace learner IDs keyed by student ID.

    Args:
        api: Brightspace api instance.
        org_id: the brightspace org (course) id to fetch learners from.

    Returns:
        A dict with student ID as the key, and brightspace learner id as the value.
    """
    id_dict = {}
    for user in api.get_classlist(org_id):
        if user.classlist_role_display_name not in ["Learner"]:
            continue
        id_dict.update({str(user.org_defined_id): user.identifier})

    return id_dict


###########################################################
###########################################################
# A suite of functions to get Plom related stuff


def restructure_plom_marks(plom_marks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Change the key on the Plom marks dicts to student number.

    **WARNING: sometimes requires user interaction.**
    This function will remove any papers with warnings attached.

    Returns:
        A list of dicts.
    """
    simplified_list = []
    # we won't attempt to push papers on the discard list to Brightspace
    discard_list = []
    for mark_dict in plom_marks:
        # Oct. 8th - the distinction between None and "" is significant
        # None means the paper was ID'd as having a blank coverpage
        # "" means the paper hasn't been ID'd yet and we will implicitly discard it
        # Oct. 24th: the API now gives only those that are ID'd so this may not happen
        if mark_dict[PLOM_STUDENT_ID] == "":
            continue

        # Oct. 8th - we explicitly discard unmarked papers
        if mark_dict[PLOM_WARNINGS]:
            discard_list.append(mark_dict)
            continue

        simplified_list.append(mark_dict)

    if discard_list:
        print(
            f"{len(discard_list)} paper[s] cannot be processed for push to Brightspace:"
        )
        print(tabulate(discard_list, headers="keys"))
        print(
            f"This script will not push these {len(discard_list)} results to Brightspace,"
        )
        confirmation = input("proceed? [Y/n] ")
        if confirmation not in ["", "y", "Y", "\n"]:
            print("CANCELLED")
            sys.exit(0)

    return simplified_list


###########################################################


def main():
    parser = get_parser()
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ModuleNotFoundError:
        pass

    # check api key
    if hasattr(args, "api_key"):
        args.api_key = args.api_key or os.environ.get("BS_TOKEN")
    if hasattr(args, "api_key") and not args.api_key:
        args.api_key = input("Please enter an access token for Brightspace: ")
    print("Checking access token... ", end="")
    api = bsapi.BSAPI(args.api_key, args.api_url)
    print(CHECKMARK)

    # check course
    if not args.org_id:
        org_id, org_name = interactively_get_org(api)
    else:
        no_match = True
        courses_teaching = get_courses_teaching(api)
        for course_id, course_name in courses_teaching:
            if args.org_id != course_id:
                continue
            # found a match
            no_match = False
            org_name = course_name
            org_id = args.org_id
            break
        if no_match:
            err = f'provided org-id: "{args.org_id}" did not match any of your taught courses:'
            err += str(courses_teaching)
            raise ValueError(err)
    print(f"Course: ({org_id}) {org_name} " + CHECKMARK)

    # check assignment
    if not args.folder_id:
        folder_id, folder_name = interactively_get_folder(api, org_id)
    else:
        no_match = True
        assignments_in_course = get_assignments(api, org_id)
        for assignment_id, assignment_name in assignments_in_course:
            if args.folder_id != assignment_id:
                continue
            # found a match
            no_match = False
            folder_name = assignment_name
            folder_id = assignment_id
            break
        if no_match:
            err = f'provided folder-id: "{args.folder_id}" did not match any assignments in your org "{org_name}":'
            err += str(assignments_in_course)
            raise ValueError(err)
    print(f"Assignment: ({folder_id}) {folder_name} " + CHECKMARK)

    # check plom credentials
    if hasattr(args, "plom_server"):
        args.plom_server = args.plom_server or os.environ.get("PLOM_SERVER")
    if hasattr(args, "plom_username"):
        args.plom_username = args.plom_username or os.environ.get("PLOM_USERNAME")
    if hasattr(args, "plom_password"):
        args.plom_password = args.plom_password or os.environ.get("PLOM_PASSWORD")

    if hasattr(args, "plom_server") and not args.plom_server:
        args.plom_server = input("plom server: ")
    if hasattr(args, "plom_username") and not args.plom_username:
        args.plom_username = input("plom username: ")
    if hasattr(args, "plom_password") and not args.plom_password:
        args.plom_password = getpass("plom password: ")

    print("Checking plom credentials... ", end="")
    plom_messenger = start_messenger(
        args.plom_server, args.plom_username, args.plom_password
    )
    print(CHECKMARK)

    # iterate over this
    student_marks = restructure_plom_marks(plom_messenger.get_paper_marks())
    print(f"Plom marks retrieved (for {len(student_marks)} examinees).")

    # dict to convert student ID to brightspace ID
    brightspace_ids = get_brightspace_learner_id_dict(api, org_id)

    successes = []
    count = 0
    brightspace_absences = []
    brightspace_timeouts = []
    plom_timeouts = []
    for plom_exam_dict in tqdm(student_marks):
        paper_number = plom_exam_dict[PLOM_PAPERNUM]
        score = plom_exam_dict[PLOM_MARKS]
        student_id = plom_exam_dict[PLOM_STUDENT_ID]
        student_name = plom_exam_dict[PLOM_STUDENT_NAME]
        try:
            student_brightspace_id = brightspace_ids[student_id]
        except KeyError:
            print(
                f"Student {student_name} - {student_id} (paper #{paper_number})"
                " couldn't be found in your brightspace course (or section if specified),"
                " skipping."
            )
            brightspace_absences.append(
                {
                    "paper_number": paper_number,
                    "student_id": student_id,
                    "error": f"{student_name} couldn't be found on Brightspace.",
                }
            )
            continue

        # must upload grades to allow file uploads
        try:
            if args.dry_run:
                successes.append(
                    {
                        "file/mark": score,
                        "student_id": student_id,
                        "student_name": student_name,
                        "student_brightspace_id": student_brightspace_id,
                    }
                )
            else:
                api.set_dropbox_folder_submission_feedback(
                    org_unit_id=org_id,
                    folder_id=folder_id,
                    entity_type=ENTITY_TYPE,
                    entity_id=student_brightspace_id,
                    score=score,
                    feedback=FEEDBACK_TEXT,
                    draft=True,  # This bool controls feedback visibility for students
                )
        except bsapi.APIError as e:
            print(e)
            brightspace_timeouts.append(
                {
                    "paper_number": paper_number,
                    "student_id": student_id,
                    "error": f'{e}\n mark "{score}" could not be uploaded.',
                }
            )
        time.sleep(random.uniform(0.1, 0.3))

        if args.papers:
            try:
                file_info = plom_messenger.get_reassembled(paper_number)
                if args.dry_run:
                    successes.append(
                        {
                            "file/mark": file_info["filename"],
                            "student_id": student_id,
                            "student_name": student_name,
                            "student_brightspace_id": student_brightspace_id,
                        }
                    )
                else:
                    # TODO - file upload to brightspace
                    api.add_dropbox_folder_submission_feedback_file(
                        org_unit_id=org_id,
                        folder_id=folder_id,
                        entity_type=ENTITY_TYPE,
                        entity_id=student_brightspace_id,
                        file_path=Path(file_info["filename"]),
                    )
            except PlomException as e:
                print(e)
                plom_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": e,
                    }
                )
            except bsapi.APIError as e:
                print(e)
                brightspace_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": e,
                    }
                )
            finally:
                try:
                    Path(file_info["filename"]).unlink(missing_ok=True)
                # if the Plom download fails, file_info won't be declared
                except NameError:
                    pass

            time.sleep(random.uniform(0.1, 0.3))

        if args.solutions:
            try:
                file_info = plom_messenger.get_solution(paper_number)
                if args.dry_run:
                    successes.append(
                        {
                            "file/mark": file_info["filename"],
                            "student_id": student_id,
                            "student_name": student_name,
                            "student_brightspace_id": student_brightspace_id,
                        }
                    )
                else:
                    # TODO - file upload to brightspace
                    api.add_dropbox_folder_submission_feedback_file(
                        org_unit_id=org_id,
                        folder_id=folder_id,
                        entity_type=ENTITY_TYPE,
                        entity_id=student_brightspace_id,
                        file_path=Path(file_info["filename"]),
                    )
            except PlomException as e:
                print(e)
                plom_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": e,
                    }
                )
            except bsapi.APIError as e:
                print(e)
                brightspace_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": e,
                    }
                )
            finally:
                try:
                    Path(file_info["filename"]).unlink(missing_ok=True)
                # if the Plom download fails, file_info won't be declared
                except NameError:
                    pass

            time.sleep(random.uniform(0.1, 0.3))

        if args.reports:
            try:
                file_info = plom_messenger.get_report(paper_number)
                if args.dry_run:
                    successes.append(
                        {
                            "file/mark": file_info["filename"],
                            "student_id": student_id,
                            "student_name": student_name,
                            "student_brightspace_id": student_brightspace_id,
                        }
                    )
                else:
                    # TODO - file upload to brightspace
                    api.add_dropbox_folder_submission_feedback_file(
                        org_unit_id=org_id,
                        folder_id=folder_id,
                        entity_type=ENTITY_TYPE,
                        entity_id=student_brightspace_id,
                        file_path=Path(file_info["filename"]),
                    )
            except PlomException as e:
                print(e)
                plom_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": e,
                    }
                )
            except bsapi.APIError as e:
                print(e)
                brightspace_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": e,
                    }
                )
            finally:
                try:
                    Path(file_info["filename"]).unlink(missing_ok=True)
                # if the Plom download fails, file_info won't be declared
                except NameError:
                    pass

            time.sleep(random.uniform(0.1, 0.3))

        count += 1

    print("\n")
    print(f"pushed {count} papers without issue\n")

    if plom_timeouts:
        print(f"{len(plom_timeouts)} FAILED DOWNLOADS FROM PLOM")
        print(tabulate(plom_timeouts, headers="keys"))
        print("\n\n")

    if brightspace_absences:
        print(f"{len(brightspace_absences)} STUDENTS ABSENT FROM BRIGHTSPACE")
        print(tabulate(brightspace_absences, headers="keys"))
        print("\n\n")

    if brightspace_timeouts:
        print(f"{len(brightspace_timeouts)} FAILED UPLOADS TO BRIGHTSPACE")
        print(tabulate(brightspace_timeouts, headers="keys"))
        print("\n\n")

    if args.dry_run:
        print("These items would've been uploaded to Brightspace:")
        print(tabulate(successes, headers="keys"))
        print("\n\n")


if __name__ == "__main__":
    main()
