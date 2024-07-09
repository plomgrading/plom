# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2021 Nicholas J H Lai

"""Utilities for canned users and auto-generated (poor) passwords."""

import math
import secrets
from random import sample

words = """
about above across act active activity add afraid after again age ago agree
air all alone along already always am amount an and angry another answer any
anyone anything anytime appear apple are area arm army around arrive art as ask
at attack aunt autumn away baby back bad bag ball bank base basket bath be bean
bear bed bedroom beer behave before begin behind bell below besides best better
between big bird birth birthday bit bite black bleed block blood blow blue board
boat body boil bone book border born borrow both bottle bottom bowl box boy
branch brave bread break breathe bridge bright bring brother brown brush build
burn business bus busy but buy by cake call can candle cap car card care careful
careless carry case cat catch central century certain chair chance change chase
cheap cheese chicken child children choice choose circle city class clever clean
clear climb clock cloth clothes cloud cloudy close coffee coat coin cold collect
colour comb common compare come complete computer continue control cook cool
copper corn corner correct cost contain count country course cover crash cross
cry cup cupboard cut dance dark daughter day dead decide decrease deep deer
depend desk destroy develop die dinner dirty discover dish do dog door double
down draw dream dress drink drive drop dry duck dust duty each ear early earn
earth east easy eat effect egg eight either electric elephant else empty end
enemy enjoy enough enter equal entrance escape even evening event ever every
everyone exact example except excited exercise expect explain eye face fact fail
fall false family famous far farm father fast fat fault fear feed feel
fever few fight fill film find fine finger finish fire first fish fit five fix
flag flat float floor flour flower fly fold food fool foot football for force
foreign forest forget forgive fork form fox four free freedom freeze fresh
friend friendly from front fruit full fun funny further future game garden gate
general get gift give glad glass go goat god gold good goodbye grass grave great
green gray ground group grow gun hair half hall hammer hand happen happy hard
hat hate have he head healthy hear heavy heart heaven height hello help hen her
here hers hide high hill him his hit hobby hold hole holiday home hope horse
hospital hot hotel house how hundred hungry hour hurry husband hurt ice idea if
in increase inside into invent iron invite is island it its jelly job join juice
jump just keep key kill kind king kitchen knee knife knock know ladder lady lamp
land large last late lately laugh lazy lead leaf learn leave leg left lend
length less lesson let letter library lie life light like lion lip list listen
little live lock lonely long look lose lot love low lower luck obey object ocean
of off offer office often oil old on one only open opposite or orange order
other our out outside over own page pain paint pair pan paper parent park part
partner party pass past path pay peace pen pencil people pepper per perfect
period person petrol piano pick picture piece pig pin pink place plane plant
plastic plate play please pleased plenty pocket point poison police polite pool
poor popular position possible potato pour power present press pretty prevent
price prince prison private prize probably problem produce promise proper
protect provide public pull punish pupil push put queen question quick quiet
quite radio rain rainy raise reach read ready real really receive record red
remember remind remove rent repair repeat reply report rest result return rice
rich ride right ring rise road rob rock room round rubber rude rule ruler run
rush sad safe sail salt same sand save say school science scissors search seat
second see seem sell send sentence serve seven several shade shadow shake
shape share sharp she sheep sheet shelf shine ship shirt shoe shoot shop short
should shoulder shout show sick side signal silence silly silver similar simple
single since sing sink sister sit six size skill skin skirt sky sleep slip slow
small smell smile smoke snow so soap sock soft some someone son soon sorry sound
soup south space speak special speed spell spend spoon sport spread spring
square stamp stand star start station stay steal steam step still stomach stone
stop store storm story strange street strong student study stupid subject such
sudden sugar suitable summer sun sunny support sure surprise sweet swim sword
table take talk tall taste taxi tea teach team tear tell ten tennis terrible
test than that the their then there these thick thin thing think third this
though threat three tidy tie title to today toe together tomorrow tonight too
tool tooth top total touch town train tram travel tree trouble true trust twice
try turn type ugly uncle under unit until up use useful usual usually very
village voice visit wait wake walk want warm was wash waste watch water way we
weak wear weather wedding week weight welcome were well west wet what wheel when
where which while white who why wide wife wild will win wind window wine winter
wire wise wish with without woman wonder word work world worry yard yell yet you
young your zero zoo
""".split()

names = """
    aiden azami basia bob caris carol dave duska erin evander fatima
    frank greg gwen haris heidi idris isla john judy kali kamal layla
    lucas mary malik nina noor olivia oscar peter peggy quentin quinci
    raisa rupert samir sybil talia trent ursula usher vanna virgil
    walter wendy xavier xena yuri yvonne zahara zeke
""".split()


def simple_password(n=3):
    """Creates a new simple password containing a number of words.

    Args:
        n (int): number of words for the password. Default n = 3.

    Returns:
        str: Password.
    """
    password = ""
    for i in range(n):
        password += secrets.choice(words)
    return password


def make_random_user_list(number):
    """Makes a list of random users and passwords.

    Args:
        number (int): how many randomly named users.  For a large number
            usernames will have random digits postfixed.

    Returns:
        list: a list of (user, password) tuples
    """
    if number > len(names):
        digits = max(2, int(math.ceil(math.log10(number / len(names)))))
        loc_names = [
            x + "{}".format(n).zfill(digits) for x in names for n in range(10**digits)
        ]
    else:
        loc_names = names
    loc_names = sample(loc_names, number)
    return [(name, simple_password()) for name in loc_names]


def make_numbered_user_list(number):
    """Makes a list of numbered users (rather than named users).

    Each user is named like "user018" where the number is zero padded
    based on the total number of users requested.

    Args:
        number (int): how many users to create.

    Returns:
        list: a list of (user, password) tuples.
    """
    digits = max(1, int(math.ceil(math.log10(number if number > 0 else 1))))
    names = ["user" + "{}".format(n).zfill(digits) for n in range(number)]
    return [(name, simple_password()) for name in names]
