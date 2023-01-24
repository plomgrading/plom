#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2023 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2021 Elizabeth Xiao
# Copyright (C) 2022 Joey Shi
# Copyright (C) 2022 Edith Coates

"""Plom tools related to producing papers, and setting up servers.

See help for each subcommand or consult online documentation for an
overview of the steps in setting up a server.

Most subcommands communicate with a server, which can be specified
on the command line or by setting environment variables PLOM_SERVER
and PLOM_MANAGER_PASSWORD.
"""

__copyright__ = "Copyright (C) 2020-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import sys
import argparse
import os
from pathlib import Path
from textwrap import dedent

from stdiomask import getpass

import plom
from plom import __version__
from plom import Default_Port
from plom import SpecVerifier
from plom.plom_exceptions import PlomExistingDatabase, PlomServerNotReady
from plom.create import process_classlist_file, get_demo_classlist, upload_classlist
from plom.create import start_messenger
from plom.create import build_database, build_papers, build_extra_page_pdf
from plom.create.demotools import buildDemoSourceFiles
from plom.create import upload_rubrics_from_file, download_rubrics_to_file
from plom.create import upload_demo_rubrics
from plom.create import clear_manager_login
from plom.create import version_map_from_file
from plom.create import save_version_map

# we may want to shift some files around
from plom.server.manageUserFiles import write_csv_user_list
from plom.server.manageUserFiles import get_raw_user_dict_from_csv
from plom.server.manageUserFiles import get_template_user_dict
from plom.server.manageUserFiles import build_canned_users


def ensure_toml_extension(fname):
    """Append a .toml extension if not present.

    Args:
        fname (pathlib.Path/str): a filename.

    Returns:
        pathlib.Path: filename with a `.toml` extension.

    Raises:
        ValueError: filename has incorrect extension (neither blank
           nor `.toml`)
    """
    fname = Path(fname)
    if fname.suffix.casefold() == ".toml":
        return fname
    if fname.suffix == "":
        return fname.with_suffix(".toml")
    raise ValueError('Your specification file should have a ".toml" extension.')


def parse_verify_save_spec(fname, *, save=False):
    fname = Path(fname)
    print(f'Parsing and verifying the specification "{fname}"')
    if not fname.exists():
        raise FileNotFoundError(f'Cannot find "{fname}": try "plom-create newspec"?')

    sv = SpecVerifier.from_toml_file(fname)
    sv.verifySpec()
    # TODO: this will create private codes: likely unwanted?
    # sv.checkCodes()
    if not save:
        return
    outfile = Path(".") / "verifiedSpec.toml"
    sv.saveVerifiedSpec(verbose=True, outfile=outfile)


def autogen_users_file(demo, auto, numbered, rawfile=Path("userListRaw.csv")):
    """Make a file of users and passwords.

    args:
        demo (bool): make canned demo with known usernames/passwords.
        auto (int or None): number of autogenerate usernames and passwords.
        numbered (bool): autogenerate usernames like "user03" and pwds.

    keyword args:
        rawfile (str/pathlib.Path): a filename to write usernames/passwords.
            Defaults to "userListRaw.csv" in the current working directory.

    return:
        pathlib.Path: the filename written to, "userListRaw.csv" by default.
    """
    rawfile = Path(rawfile)
    if rawfile.exists():
        raise FileExistsError(f"File {rawfile} already exists: remove and try again.")

    if demo:
        print(
            f"Creating a demo user list at {rawfile}. ** DO NOT USE ON REAL SERVER **"
        )
        users = get_template_user_dict()
        users.pop("manager")
        users = [(k, v) for k, v in users.items()]
        write_csv_user_list(users, rawfile)
        return rawfile

    assert auto is not None, "auto cannot be None unless demo is specified"

    print(
        'Creating an auto-generated {} user list at "{}"'.format(
            "numbered" if numbered else "named",
            rawfile,
        )
    )
    users = build_canned_users(auto, numbered=numbered, manager=False)
    write_csv_user_list(users, rawfile)
    return rawfile


def get_parser():
    def check_non_negative(arg):
        if int(arg) < 0:
            raise ValueError
        return int(arg)

    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="\n".join(__doc__.split("\n")[1:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    sub = parser.add_subparsers(
        dest="command", description="Perform tasks related to building tests."
    )

    sp_status = sub.add_parser(
        "status",
        help="Status of the server",
        description="Information about the server.",
    )

    sp_newspec = sub.add_parser(
        "newspec",
        aliases=["new"],
        help="Create new spec file",
        description="Create new spec file.",
    )
    group = sp_newspec.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "specFile",
        nargs="?",
        default="testSpec.toml",
        help="defaults to '%(default)s'.",
    )
    group.add_argument(
        "--demo",
        action="store_true",
        help="Use an auto-generated demo test. **Obviously not for real use**",
    )
    sp_newspec.add_argument(
        "--demo-num-papers",
        type=int,
        # default=20,  # we want it to give None
        metavar="N",
        help="How many fake exam papers for the demo (defaults to 20 if omitted)",
    )

    # seems like this should hide it but it does not
    # spP = sub.add_parser("parse", help=argparse.SUPPRESS)
    spP = sub.add_parser("parse", help="Parse spec file (REMOVED)")

    spP = sub.add_parser(
        "validatespec",
        help="Check a spec file for validity.",
        description="""Parse and verify a test-specification toml file.""",
    )
    spP.add_argument(
        "specFile",
        nargs="?",
        default="testSpec.toml",
        help="defaults to '%(default)s'.",
    )
    spP.add_argument(
        "--save",
        action="store_true",
        help="""
            By default the verified spec file is not saved.
            Pass this to write it to 'verifiedSpec.toml'.
        """,
    )

    sp_uploadspec = sub.add_parser(
        "uploadspec",
        help="Upload spec to server",
        description="Upload exam specification to server.",
    )
    sp_uploadspec.add_argument(
        "specFile",
        nargs="?",
        default="testSpec.toml",
        help="defaults to '%(default)s'.",
    )

    sp_class = sub.add_parser(
        "class",
        help="Read in a classlist",
        description="Get student names/numbers from csv, process, and upload to server.",
        epilog=dedent(
            """
            The classlist can be a .csv file exported from Canvas (specifically,
            Canvas -> Grades -> Actions -> Export).  Plom will do some light sanity
            checking such as dropping names like "Test Student".

            Alternatively, the classlist can be a .csv file with column headers:
              * id - student ID number
              * name - student name in a single field
              * paper_number - the test-number to assign to that student for
                               prenaming papers. If unsure, include the column,
                               but leave it blank. Each paper_number must be
                               unique and in the range [1, NumberToProduce]
                               but they need not be contiguous nor ordered.

            Plom will accept uppercase or lowercase column headers.
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sp_class.add_argument(
        "-i",
        "--ignore-warnings",
        action="store_true",
        help="Ignore any classlist warnings and upload anyway.",
    )

    group = sp_class.add_mutually_exclusive_group(required=True)
    group.add_argument("classlist", nargs="?", help="filename in csv format")
    group.add_argument(
        "--demo",
        action="store_true",
        help="Use auto-generated classlist. **DO NOT USE ON REAL SERVER**",
    )
    sp_class.add_argument(
        "--force",
        action="store_true",
        help="""
            By default, it is an error to upload a new classlist.
            This overrides that check; for which you accept responsibility.
            If you are using "numberToProduce = -1" then the first classlist
            will have chosen a value; you may want to reupload your spec
            before pushing a second classlist.
            This is a non-exaustive list of what could go wrong.
            If you've already produced and printed papers, you should be
            careful with this option, although we are not aware of any
            specific problems it would cause.
        """,
    )

    spDB = sub.add_parser(
        "make-db",
        help="Populate the database",
        description="""
            See "make" below, but here only the database is populated and
            no papers will be built.  You can then call "make" later.""",
    )
    spDB.add_argument(
        "--from-file",
        metavar="FILE",
        help="Read the version map from FILE.  WORK-IN-PROGRESS!",
    )

    spQVM = sub.add_parser(
        "get-ver-map",
        help="Save question-version map from the database",
        description="""
            The question-version map shows which questions have which
            version for each paper.
            This map is created server-side by the 'make-db' command.
            This .csv file can be used to reconstruct the database in
            case of catastrophe: we recommend keeping a backup copy.
        """,
    )
    spQVM.add_argument(
        "file",
        nargs="?",
        help="""
            Filename, csv or json format.  Default: 'question_version_map.csv'.
        """,
    )

    spB = sub.add_parser(
        "make",
        help="Make the PDFs",
        description="""
            Build papers (and if necessary the database) from the test
            specification.  Based on the classlist "paper_num" column,
            some of the papers may have names printed on them from the
            classlist ("pre-named") and the remainder will be blank.
            As they are created, the prenamed papers will be inserted
            into the prediction table with the predictor set to "prename".
            If you want to change the prenames: (1) force upload a new
            classlist, and (2) see the "predictions" command to erase
            the "prename" predictor.
        """,
    )
    spB.add_argument(
        "--no-pdf",
        action="store_true",
        help="Do not generate real PDFs - instead generate empty files.",
    )
    spB.add_argument(
        "--without-qr",
        action="store_true",
        help="Produce PDFs without QR codes and staple-corner indicators.",
    )
    spB.add_argument(
        "-n", "--number", type=int, help="used for building a specific paper number"
    )
    spB.add_argument(
        "-x",
        "--namebox-xpos",
        metavar="X",
        type=float,
        help="""
            Specify horizontal centre of the name/ID box that will be printed
            on named papers, a float from 0 (left) to 100 (right) of the page.
            Defaults to 50.""",
    )
    spB.add_argument(
        "-m",
        "-y",
        "--namebox-ypos",
        metavar="Y",
        type=float,
        help="""
            Specify vertical location of the name/ID that will be printed on
            named papers, a float from 0 (top) to 100 (bottom) of the
            page.
            Defaults to 42.""",
    )

    sub.add_parser(
        "extra-pages",
        help="Make an extra pages PDF",
        description="""
          Make a simple extra-paper PDF for students to use when they need more
          space.
        """,
    )

    sp_user = sub.add_parser(
        "user",
        help="Add/modify a user account.",
        description="""
          Add a new user account.  You can provide a password or one will be
          autogenerated and echoed to the screen. Use the --update argument
          to modify an existing user's password instead.
          TODO: support disable/enable and maybe delete?
        """,
    )
    sp_user.add_argument(
        "--update", action="store_true", help="Update an existing user's password."
    )
    sp_user.add_argument(
        "username",
        nargs="?",
        help="The username",
    )
    sp_user.add_argument(
        "userpassword",
        nargs="?",
        help="Autogenerated xkcd-style if omitted.",
    )

    sp_users = sub.add_parser(
        "users",
        help="Create/manipulate user accounts",
        description="""
          Manipulate users accounts.  With no arguments, list the users already
          on the server.
          Given a filename, parses a plain-text user list, and creates them
          on the server.
          Can also produce a template file for you to edit, with autogenerated
          passwords.
        """,
    )
    group = sp_users.add_mutually_exclusive_group()
    group.add_argument(
        "userlist", nargs="?", help="Create/update a list of users from a csv file."
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="""List the users on the server (default behaviour).""",
    )
    group.add_argument(
        "--demo",
        action="store_true",
        help="""
            Use fixed prepopulated demo userlist and passwords.
            **DO NOT USE THIS ON REAL SERVER**.
            Includes "scanner" and "reviewer" BUT NOT "manager" accounts
            (because the server must already have that).
        """,
    )
    group.add_argument(
        "--auto",
        type=check_non_negative,
        metavar="N",
        help="""
            Auto-generate a random user list of N users with real-ish usernames.
            This will also create "scanner" and "reviewer" accounts BUT NOT a
            "manager" account (because the server must already have that).
        """,
    )
    # TODO: goes with --auto
    sp_users.add_argument(
        "--numbered",
        action="store_true",
        help='Use numbered usernames, e.g. "user17", for the autogeneration.',
    )
    sp_users.add_argument(
        "--no-upload",
        action="store_false",
        dest="upload",
        help="Do not upload, just create a local template file.",
    )

    sp_pred = sub.add_parser(
        "predictions",
        help="Manipulate servers prediction lists",
        description="""
            Before papers are identified, there can exist various predictions
            about which paper goes with which individual.  "Prenamed" is one
            example, where names are pre-printed on the ID sheet.
            Computer vision tools also make predictions based on student ID
            numbers.
        """,
    )
    group = sp_pred.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--predictor",
        type=str,
        metavar="P",
        help="Show all predictions by the predictor P.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Show all predictions.",
    )
    group.add_argument(
        "--erase",
        type=str,
        metavar="P",
        help="""
            Erase all predictions by the predictor P.
            Caution: think carefully before erasing the "prename" predictor.
        """,
    )

    sp_rubric = sub.add_parser(
        "rubric",
        help="Add pre-build rubrics",
        description="""
            Add pre-made rubrics to the server.  Your graders will be able to
            build their own rubrics but if you have premade rubrics you can
            add them here or by using the plom-manager tool.
            This tool can also dump the current rubrics from a running server.""",
    )
    group = sp_rubric.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dump",
        type=str,
        metavar="FILE",
        help="""Dump the current rubrics from SERVER into FILE,
            which can be a .toml, .json, or .csv file.
            Defaults to FILE.toml if no extension specified..""",
    )
    group.add_argument(
        "rubric_file",
        nargs="?",
        help="""
            Upload a pre-build list of rubrics from this file.
            This can be a .json, .toml or .csv file.""",
    )
    group.add_argument(
        "--demo",
        action="store_true",
        help="Upload an auto-generated rubric list for demos.",
    )

    sp_tags = sub.add_parser(
        "tags",
        help="List tags",
        description="""
          List all the tags defined on the server.
        """,
    )
    sp_tags.add_argument(
        "--list",
        action="store_true",
        help="""List the tags on the server (default behaviour).""",
    )

    sp_tag = sub.add_parser(
        "tag",
        help="Add/remove tags from papers",
        description="""
          Add or remove tags from a paper and question.
        """,
    )
    sp_tag.add_argument(
        "--rm",
        action="store_true",
        help="""Remove tag(s) from paper (if omitted we add tags).""",
    )
    sp_tag.add_argument(
        "task",
        nargs=1,
        help="""
            Which task to tag, e.g., q0123g4 for paper 123 question 4.
        """,
    )
    sp_tag.add_argument("tags", nargs="+", help="Tag(s) to add to task.")

    sp_clear = sub.add_parser(
        "clear",
        help='Clear "manager" login',
        description='Clear "manager" login after a crash or other expected event.',
    )

    for sp in (
        sp_status,
        sp_uploadspec,
        spDB,
        spQVM,
        spB,
        sp_class,
        sp_user,
        sp_users,
        sp_pred,
        sp_rubric,
        sp_tags,
        sp_tag,
        sp_clear,
    ):
        sp.add_argument(
            "-s",
            "--server",
            metavar="SERVER[:PORT]",
            action="store",
            help=f"""
                Which server to contact, port defaults to {Default_Port}.
                Also checks the environment variable PLOM_SERVER if omitted.
                If the WEBPLOM environment variable is set, talk to a Django
                server instead (EXPERIMENTAL!)
            """,
        )
        sp.add_argument(
            "-w",
            "--password",
            type=str,
            help="""
                for the "manager" user, also checks the
                environment variable PLOM_MANAGER_PASSWORD.
            """,
        )

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    if hasattr(args, "server"):
        args.server = args.server or os.environ.get("PLOM_SERVER")

    if hasattr(args, "password"):
        args.password = args.password or os.environ.get("PLOM_MANAGER_PASSWORD")
        if not args.password:
            args.password = getpass('Please enter the "manager" password: ')

    if args.command == "status":
        plom.create.status(msgr=(args.server, args.password))

    elif args.command == "newspec" or args.command == "new":
        if args.demo:
            fname = "demoSpec.toml"
        else:
            fname = ensure_toml_extension(args.specFile)

        if args.demo_num_papers:
            assert args.demo, "cannot specify number of demo paper outside of demo mode"
        if args.demo:
            print("DEMO: creating demo test specification file")
            SpecVerifier.create_demo_template(
                fname, num_to_produce=args.demo_num_papers
            )
            print("DEMO: creating demo solution specification file")
            SpecVerifier.create_demo_solution_template("solutionSpec.toml")

        else:
            print('Creating specification file from template: "{}"'.format(fname))
            print('  * Please edit the template spec "{}"'.format(fname))
            SpecVerifier.create_template(fname)
            print("Creating solution specification file template = solutionSpec.toml")
            print(
                "  **Optional** - Please edit the template solution spec if you are including solutions in your workflow."
            )
            SpecVerifier.create_solution_template("solutionSpec.toml")
        print('Creating "sourceVersions" directory for your test source PDFs.')
        Path("sourceVersions").mkdir(exist_ok=True)
        if not args.demo:
            print("  * Please copy your test in as version1.pdf, version2.pdf, etc.")
        if args.demo:
            print(
                "DEMO: building source files: version1.pdf, version2.pdf, solution1.pdf, solutions2.pdf"
            )
            if not buildDemoSourceFiles(solutions=True):
                sys.exit(1)
            print(
                f'DEMO: please upload the spec to a server using "plom-create uploadspec {fname}"'
            )

    elif args.command == "parse":
        raise NotImplementedError(
            'The "parse" command has been removed, see "validatespec" and/or "uploadspec"'
        )

    elif args.command == "validatespec":
        fname = ensure_toml_extension(args.specFile)
        parse_verify_save_spec(fname, save=args.save)

    elif args.command == "uploadspec":
        fname = ensure_toml_extension(args.specFile)
        sv = SpecVerifier.from_toml_file(fname)
        sv.verifySpec()
        sv.checkCodes()
        print("spec seems ok: we will upload it to the server")
        msgr = start_messenger(args.server, args.password)
        try:
            # TODO: sv.spec versus sv.get_public_spec_dict()?
            # TODO: think about who is supposed to know/generate the privateSeed
            msgr.upload_spec(sv.spec)
        finally:
            msgr.closeUser()
            msgr.stop()

    elif args.command == "class":
        msgr = start_messenger(args.server, args.password)
        try:
            try:
                spec = msgr.get_spec()
            except PlomServerNotReady:
                print("Server does not yet have a test-spec. We cannot proceed.")
                sys.exit(1)  # TODO = more graceful exit

            if args.demo:
                classlist = get_demo_classlist(spec)
                upload_classlist(classlist, msgr=msgr, force=args.force)
            else:
                success, classlist = process_classlist_file(
                    args.classlist, spec, ignore_warnings=args.ignore_warnings
                )
                if success:
                    try:
                        upload_classlist(classlist, msgr=msgr, force=args.force)
                    except Exception as err:  # TODO - make a better error handler here
                        print(
                            "An error occurred when uploading the valid classlist: ",
                            err,
                        )
                else:
                    print("Could not process classlist - see messages above")
        finally:
            msgr.closeUser()
            msgr.stop()

    elif args.command == "make-db":
        if args.from_file is None:
            build_database(msgr=(args.server, args.password))
        else:
            qvmap = version_map_from_file(args.from_file)
            build_database(vermap=qvmap, msgr=(args.server, args.password))

    elif args.command == "get-ver-map":
        f = save_version_map(args.file, msgr=(args.server, args.password))
        print(f"Question-version map saved to {f}")

    elif args.command == "make":
        try:
            build_database(msgr=(args.server, args.password))
        except PlomExistingDatabase:
            print("Since we already have a database, move on to making papers")
        build_papers(
            fakepdf=args.no_pdf,
            no_qr=args.without_qr,
            indexToMake=args.number,
            xcoord=args.namebox_xpos,
            ycoord=args.namebox_ypos,
            msgr=(args.server, args.password),
        )
    elif args.command == "extra-pages":
        print("Building extra page in case students need more space...")
        build_extra_page_pdf(destination_dir=Path.cwd())
        print('See "extra_page.pdf" in the current directory')

    elif args.command == "user":
        msgr = start_messenger(args.server, args.password)
        try:
            from plom.aliceBob import simple_password

            if args.userpassword:
                pwd = args.userpassword
            else:
                pwd = simple_password()
                print(f'Creating/updating user with password "{pwd}"')

            if args.update:
                ok, msg = msgr.changeUserPassword(args.username, pwd)
            else:
                ok, msg = msgr.createUser(args.username, pwd)
        finally:
            msgr.closeUser()
            msgr.stop()
        if ok:
            print(f"Success: {msg}")
        else:
            print(f"Failed: {msg}")
            sys.exit(1)

    elif args.command == "users":
        if args.list or (not args.demo and args.auto is None and not args.userlist):
            msgr = start_messenger(args.server, args.password)
            try:
                user_dict = msgr.getUserDetails()
            finally:
                msgr.closeUser()
                msgr.stop()
            print("Users:")
            for user, stuff in user_dict.items():
                stuffit = "\t".join(str(x) for x in stuff)
                print(f"  {user:10}\t{stuffit}")
            if "scanner" not in user_dict:
                print('WARNING: server has no "scanner" user')
            if "reviewer" not in user_dict:
                print('WARNING: server has no "reviewer" user')
            return

        if args.demo or args.auto is not None:
            f = autogen_users_file(args.demo, args.auto, args.numbered)
            print(f'Template csv for user lists written to "{f}"')

        elif args.userlist:
            print(f'Creating/modifying the users in "{args.userlist}"')
            f = args.userlist

        if args.upload:
            users = get_raw_user_dict_from_csv(f)
            msgr = start_messenger(args.server, args.password)
            all_ok = True
            try:
                for user, pw in users.items():
                    ok, msg = msgr.createUser(user, pw)
                    if ok:
                        print(f'  user "{user}" success:\t{msg}')
                    else:
                        print(f'  user "{user}" failed:\t{msg}')
                        all_ok = False
                user_dict = msgr.getUserDetails()
            finally:
                msgr.closeUser()
                msgr.stop()
            if not all_ok:
                print("One or more failures create/updating users")
                sys.exit(1)
            if "scanner" not in user_dict:
                print('WARNING: server still has no "scanner" user')
            if "reviewer" not in user_dict:
                print('WARNING: server still has no "reviewer" user')

        else:
            print(f'Created "{f}" - edit passwords, add users as you see fit')
            print(f'Then upload with "plom-create users {f}"')

    elif args.command == "predictions":
        msgr = start_messenger(args.server, args.password)
        try:
            if args.predictor:
                A = msgr.IDgetPredictionsFromPredictor(args.predictor)
                for k, v in A.items():
                    print(f"{k}: {v}")
            elif args.all:
                A = msgr.IDgetPredictions()
                for k, v in A.items():
                    print(f"{k}: {v}")
            elif args.erase:
                # TODO: send back a number: "42 predictions cleared"?
                msgr.ID_delete_predictions_from_predictor(predictor=args.erase)
                print(f'Erased all predictions by "{args.erase}"')
        finally:
            msgr.closeUser()
            msgr.stop()

    elif args.command == "rubric":
        msgr = start_messenger(args.server, args.password)
        try:
            if args.demo:
                N = upload_demo_rubrics(msgr=msgr)
                print(f"Uploaded {N} demo rubrics")
            elif args.dump:
                download_rubrics_to_file(Path(args.dump), msgr=msgr)
            else:
                upload_rubrics_from_file(Path(args.rubric_file), msgr=msgr)
        finally:
            msgr.closeUser()
            msgr.stop()

    elif args.command == "tags":
        msgr = start_messenger(args.server, args.password)
        try:
            # if not args.list:
            #     print("default behaviour")
            tags = msgr.get_all_tags()
            print("Tags on server:\n    " + "\n    ".join(t for tid, t in tags))
        finally:
            msgr.closeUser()
            msgr.stop()

    elif args.command == "tag":
        msgr = start_messenger(args.server, args.password)
        try:
            # TODO: probably we want something sane like --paper 123 --question 4
            # task = f"q{paper:04}g{question}"
            (task,) = args.task
            if args.rm:
                print(f"Task {task}, removing tags: {args.tags}")
                for t in args.tags:
                    msgr.remove_single_tag(task, t)
            else:
                print(f"Task {task}, adding tags: {args.tags}")
                for t in args.tags:
                    msgr.add_single_tag(task, t)
        finally:
            msgr.closeUser()
            msgr.stop()

    elif args.command == "clear":
        clear_manager_login(args.server, args.password)
    else:
        # no command given so print help.
        parser.print_help()


if __name__ == "__main__":
    main()
