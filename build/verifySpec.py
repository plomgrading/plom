import toml
import random


# a couple of useful functions
def isPositiveInt(s):
    try:
        n = int(s)
        if n > 0:
            return True
        else:
            return False
    except ValueError:
        return False


def isContiguousListPosInt(l, lastPage):
    # check it is a list
    if type(l) is not list:
        return False
    # check each entry is 0<n<=lastPage
    for n in l:
        if not isPositiveInt(n):
            return False
        if n > lastPage:
            return False
    # check it is contiguous
    sl = set(l)
    for n in range(min(sl), max(sl) + 1):
        if n not in sl:
            return False
    # all tests passed
    return True


# define all the specification checks
def check_keys(spec):
    print("Check specification keys")
    # check it contains required keys
    for x in [
        "name",
        "longName",
        "sourceVersions",
        "totalPages",
        "numberToProduce",
        "numberToName",
        "numberOfGroups",
        "idPages",
        "doNotMark",
    ]:
        if x not in spec:
            print('Specification error - must contain "{}" but does not.'.format(x))
            exit(1)
        else:
            print('\tcontains "{}" - check'.format(x))
    # check it contains at least 1 group to mark
    if "1" in spec:
        print('\tcontains at least 1 group (ie "plom.1") - check')
    else:
        print(
            "Specification error - must contain at least 1 group to mark but does not."
        )
        exit(1)


def check_name_and_production_numbers(spec):
    print("Check specification name and numbers")
    # check name is alphanumeric and non-zero length
    print("\tChecking names")
    if spec["name"].isalnum() and len(spec["name"]) > 0:
        print('\t\tname "{}" has non-zero length - check'.format(spec["name"]))
        print('\t\tname "{}" is alphanumeric string - check'.format(spec["name"]))
    else:
        print(
            "Specification error - Test name must be an alphanumeric string of non-zero length."
        )
        exit(1)

    if (
        all(x.isalnum() or x.isspace() for x in spec["longName"])
        and len(spec["longName"]) > 0
    ):
        print('\t\tName "{}" has non-zero length - check'.format(spec["longName"]))
        print('\t\tName "{}" is alphanumeric string - check'.format(spec["longName"]))
    else:
        print(
            "Specification error - Test longName must be an alphanumeric string of non-zero length."
        )
        exit(1)

    print("\tChecking production numbers")
    # all should be positive integers
    for x in [
        "sourceVersions",
        "totalPages",
        "numberToProduce",
        "numberToName",
        "numberOfGroups",
    ]:
        if isPositiveInt(spec[x]):
            print('\t\t"{}" = {} is positive integer - check'.format(x, spec[x]))
        else:
            print('Specification error - "{}" must be a positive integer.')
            exit(1)
    # have to produce more papers than named papers - preferably with some margin of spares
    if spec["numberToProduce"] < spec["numberToName"]:
        print(
            "Specification error - You are producing fewer papers {} than you wish to name {}. Produce more papers.".format(
                spec["numberToProduce"], spec["numberToName"]
            )
        )
        exit(1)
    else:
        print(
            "\t\tTotal number of papers is larger than number of named papers - check"
        )
        if spec["numberToProduce"] < 1.05 * spec["numberToName"]:
            print(
                "WARNING = you are not producing less than 5\% un-named papers. We recommend that you produce more un-named papers"
            )
        else:
            print("\t\tProducing sufficient spare papers - check")

    for k in range(spec["numberOfGroups"]):
        if str(k + 1) in spec:
            print(
                "\t\tFound group {} of {} - check".format(k + 1, spec["numberOfGroups"])
            )
        else:
            print("Specification error - could not find group {} ".format(k + 1))
            exit(1)


def check_IDPages(ispec, lastPage):
    print("Checking IDpages")
    if "pages" not in ispec:
        print('IDpages error - could not find "pages" key')
        exit(1)
    if not isContiguousListPosInt(ispec["pages"], lastPage):
        print(
            'IDpages error - "pages" = {} should be a list of positive integers in range'.format(
                ispec["pages"]
            )
        )
        exit(1)
    else:
        print("\t\tIDpages is contiguous list of positive integers - check")
    # check that page 1 is in there.
    if ispec["pages"][0] != 1:
        print(
            "Warning - page 1 is not part if your ID pages - are you sure you want to do this?"
        )


def check_doNotMark(dspec, lastPage):
    print("Checking DoNotMark-pages")
    if "pages" not in dspec:
        print('DoNotMark pages error - could not find "pages" key')
        exit(1)
    if type(dspec["pages"]) is not list:
        print(
            'DoNotMark pages error - "pages" = {} should be a list of positive integers'.format(
                dspec["pages"]
            )
        )
        exit(1)
    # should be a list of positive integers
    for n in dspec["pages"]:
        if isPositiveInt(n) and n < lastPage:
            pass
        else:
            print(
                'DoNotMark pages error - "pages" = {} should be a list of positive integers in range'.format(
                    dspec["pages"]
                )
            )
            exit(1)
    print("\t\tDoNotMark pages is list of positive integers - check")


def check_group(gspec, lastPage):
    print("\tChecking group.{}".format(g + 1))
    # each group has keys
    for x in ["pages", "select", "mark"]:
        if x not in gspec:
            print("Group error - could not find {} key".format(x))
            exit(1)
    # check pages is contiguous list of positive integers
    if isContiguousListPosInt(gspec["pages"], lastPage):
        print(
            "\t\tpages {} is list of contiguous positive integers - check".format(
                gspec["pages"]
            )
        )
    else:
        print(
            "Group error - pages {} is not list of contiguous positive integers".format(
                gspec["pages"]
            )
        )
        exit(1)
    # check mark is positive integer
    if isPositiveInt(gspec["mark"]):
        print("\t\tmark {} is positive integer - check".format(gspec["mark"]))
    else:
        print("Group error - mark {} is not a positive integer".format(gspec["mark"]))
        exit(1)
    # check select is "fixed" or "shuffle"
    if gspec["select"] in ["fixed", "shuffle"]:
        print('\t\tselect is "fixed" or "shuffle" - check')
    else:
        print(
            'Group error - select {} is not "fixed" or "shuffle"'.format(
                gspec["select"]
            )
        )
        exit(1)


def check_pages(spec):
    print("Checking all pages used exactly once:")
    pageUse = {k + 1: 0 for k in range(spec["totalPages"])}
    for p in spec["idPages"]["pages"]:
        pageUse[p] += 1
    for p in spec["doNotMark"]["pages"]:
        pageUse[p] += 1
    for g in range(spec["numberOfGroups"]):
        for p in spec[str(g + 1)]["pages"]:
            pageUse[p] += 1
    for p in range(1, spec["totalPages"] + 1):
        if pageUse[p] != 1:
            print("Page Use error - page {} used {} times".format(p, pageUse[p]))
            exit(1)
        else:
            print("\tPage {} used once - check".format(p))


## Now actually run the checks

# read the whole spec toml file into a dict - it will have single key = "plom" with value being a dict
wholeSpec = toml.load("testSpec.toml")
# this is a dictionary that should contain "plom" as the primary key.
if "plom" not in wholeSpec:
    print('Specification format incorrect - must contain "plom"')
    exit(1)

# extract the spec itself
spec = wholeSpec["plom"]  # the spec itself

# check that spec contains required attributes
check_keys(spec)

check_name_and_production_numbers(spec)

lastPage = spec["totalPages"]

check_IDPages(spec["idPages"], lastPage)

check_doNotMark(spec["doNotMark"], lastPage)

print("Checking groups")
for g in range(spec["numberOfGroups"]):
    check_group(spec[str(g + 1)], lastPage)

check_pages(spec)

# now check and set public and private codes

if "privateCode" in spec:
    print("WARNING - privateSeed is already set. Not replacing this.")
else:
    print("Assigning a privateSeed to the spec - check")
    wholeSpec["plom"]["privateSeed"] = str(random.randrange(0, 10 ** 16)).zfill(16)

if "publicCode" in spec:
    print("WARNING - publicCode is already set. Not replacing this.")
else:
    print("Assigning a publicCode to the spec - check")
    wholeSpec["plom"]["publicCode"] = str(random.randrange(0, 10 ** 6)).zfill(6)

with open("verifiedSpec.toml", "w+") as fh:
    toml.dump(wholeSpec, fh)
