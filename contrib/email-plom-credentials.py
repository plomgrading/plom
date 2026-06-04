#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2025 Forest Kobayashi
# Copyright (C) 2024-2026 Mudit Aggarwal
# Copyright (C) 2026 Aidan Murphy

"""Distribute Plom credentials for one or more servers via email.

This script assumes you use email addresses as usernames on your Plom
server[s]. The email message template is MESSAGE_TEMPLATE, and should be
adjusted to suit your needs.

There are some defaults in place for use in the UBC math dept.
"""

__copyright__ = "Copyright (C) 2020-2026 Forest Kobayashi, Mudit Aggarwal, et. al"
__credits__ = "UBC Math dept. Graduate students"
__license__ = "AGPL-3.0-or-later"
__version__ = "0.1.0"

import argparse
import smtplib
import ssl
from csv import DictReader
from stdiomask import getpass

__DEFAULT_SMTP_SERVER__ = "mailhost.math.ubc.ca"
__DEFAULT_SMTP_SERVER_PORT__ = 465

CSV_COLUMN_USERNAME = "Username"
CSV_COL_PASSWORD_LINK = "Reset Link"

MESSAGE_TEMPLATE = r"""Subject: {assessment_name} Plom credentials
To: {receiver_email}
From: {sender_email}
CC: {cced_emails}

*This is an automatically-generated email*

Your Plom login information for marking '{assessment_name}' is given below.
----------------------------------------------------------------------
{server_string}
----------------------------------------------------------------------

Setting Passwords and Testing Credentials:
----------------------------------------------------------------------
After receiving this email please go to the links provided and set your own password. The links will expire in ten days.
You can check that your credentials are working by launching and logging in to the Plom client.
----------------------------------------------------------------------

To download the Plom client:
----------------------------------------------------------------------
1) Go to the releases page: https://gitlab.com/plom/plom-client/-/releases
2) Under "Packages" find the architecture matching your machine and download the package.
3) Launch the downloaded package.
   MacOS users may be told the Plom client can't be opened because "Apple cannot check it for malicious software". Instructions to bypass this are here: https://gitlab.com/plom/plom/-/issues/1676.
----------------------------------------------------------------------



Best,
{sender_shortname}"""


def get_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="\n".join(__doc__.split("\n")[1:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument(
        "csvfiles",
        nargs="+",
        help="One or more CSV files with column headers 'Username', and 'Reset Link'.",
    )
    parser.add_argument(
        "--sender-email",
        required=True,
        help="The email address from which emails are sent.",
    )
    parser.add_argument("--sender-password", help="The password for 'sender-email'.")
    parser.add_argument(
        "--sender-shortname",
        help="The signoff for each email. If blank, the 'sender-email' is used.",
    )
    parser.add_argument(
        "--smtp-server",
        help="The smtp server which the 'sender-email' belongs to."
        f" It defaults to {__DEFAULT_SMTP_SERVER__}",
        default=__DEFAULT_SMTP_SERVER__,
    )
    parser.add_argument(
        "--smtp-server-port",
        help="The port on the smtp server."
        f" It defaults to {__DEFAULT_SMTP_SERVER_PORT__}",
        default=__DEFAULT_SMTP_SERVER_PORT__,
    )
    parser.add_argument(
        "--assessment-name",
        required=True,
        help="A name to refer to the assessment.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print emails to stdout, rather than sending them.",
    )

    return parser


def parse_password_link(reset_link: str) -> tuple[str, str]:
    """Parse the server url from a password reset link.

    Args:
        reset_link: a standard password reset link from Plom.

    Returns:
        The Plom server url.
    """
    # 25th of May, 2026 - a reset link looks something like this:
    # https://quizdev.math.ubc.ca:59508/reset/MjQ/d3suox-4bfc1c2849ff8658763e912a
    # or this:
    # https://quizdev.math.ubc.ca/path0/reset/MjQ/d3suox-4bfc1c2849ff8658763e912a
    split_link = reset_link.split("/reset/")
    server_name = split_link[0] + "/"
    return server_name


def read_csv_files(filepath_list: list[str]) -> dict[str, dict[str, str]]:
    """Parse several csv files containing usernames and credentials.

    The csv files should be the standard output from Plom's
    'create users via csv' action.
    """
    server_info_dicts = {}

    for filepath in filepath_list:
        with open(filepath) as f:
            reader = DictReader(f)
            for row in reader:

                if row[CSV_COLUMN_USERNAME] not in server_info_dicts:
                    server_info_dicts[row[CSV_COLUMN_USERNAME]] = []

                server_name = parse_password_link(row[CSV_COL_PASSWORD_LINK])
                server_info_dicts[row[CSV_COLUMN_USERNAME]].append(
                    {
                        "server_name": server_name,
                        "reset_link": row[CSV_COL_PASSWORD_LINK],
                    }
                )
    return server_info_dicts


def main():
    """Parse args and send emails."""
    args = get_parser().parse_args()

    if not args.sender_shortname:
        args.sender_shortname = args.sender_email

    if hasattr(args, "sender_password") and not args.sender_password:
        args.sender_password = getpass(f"password for {args.sender_email}: ")

    user_dicts = read_csv_files(args.csvfiles)

    # construct credential strings for each user
    server_strings = {}
    for email, server_dict_list in user_dicts.items():
        credential_string = ""
        for server_dict in server_dict_list:
            credential_string += "===================================\n"
            credential_string += f"server: {server_dict['server_name']}\n"
            credential_string += f"username: {email}\n"
            credential_string += f"password reset link: {server_dict['reset_link']}\n"
            credential_string += "==================================="
        server_strings[email] = credential_string

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        args.smtp_server, args.smtp_server_port, context=context
    ) as server:
        server.login(args.sender_email, args.sender_password)

        for receiver_email, server_string in server_strings.items():
            message = MESSAGE_TEMPLATE.format(
                assessment_name=args.assessment_name,
                receiver_email=receiver_email,
                sender_email=args.sender_email,
                cced_emails="",
                server_string=server_string,
                sender_shortname=args.sender_shortname,
            )

            print(f"sending to {receiver_email}")
            if args.dry_run:
                print("*" * 80)
                print("dry-run")
                print(message)
                print("*" * 80)
            else:
                server.sendmail(args.sender_email, receiver_email, message)


if __name__ == "__main__":
    main()
