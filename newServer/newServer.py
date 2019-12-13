__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPLv3"

# ----------------------

from aiohttp import web, MultipartWriter, MultipartReader
import hashlib
import json
import os
import ssl
import uuid

# ----------------------

from examDB import *
from specParser import SpecParser
from authenticate import Authority

# ----------------------

serverInfo = {"server": "127.0.0.1", "mport": 41984}
# ----------------------
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
sslContext.load_cert_chain("../resources/mlp-selfsigned.crt", "../resources/mlp.key")

# aiohttp-ificiation of things
routes = web.RouteTableDef()


# ----------------------
@routes.put("/admin/knownPages/{tpv}")
async def uploadKnownPage(request):
    reader = MultipartReader.from_response(request)
    code = request.match_info["tpv"]

    part0 = await reader.next()  # should be parameters
    if part0 is None:  # weird error
        return web.Response(status=406)  # should have sent 3 parts
    param = await part0.json()
    print(param)

    part1 = await reader.next()  # should be the image file
    if part1 is None:  # weird error
        return web.Response(status=406)  # should have sent 3 parts
    image = await part1.read()
    # file it away.
    rmsg = peon.addKnownPage(
        param["test"],
        param["page"],
        param["version"],
        param["fileName"],
        image,
        param["md5sum"],
    )
    return web.json_response(rmsg, status=200)  # all good


# ----------------------


class Server(object):
    def __init__(self, spec, db):
        self.testSpec = spec
        self.DB = db
        self.loadUsers()

    def loadUsers(self):
        """Load the users from json file, add them to the authority which
        handles authentication for us.
        """
        if os.path.exists("../resources/userList.json"):
            with open("../resources/userList.json") as data_file:
                # Load the users and pass them to the authority.
                self.userList = json.load(data_file)
                self.authority = Authority(self.userList)
        else:
            # Cannot find users - give error and quit out.
            print("Where is user/password file?")
            quit()

    def addKnownPage(self, t, p, v, fname, image, md5o):
        # create a filename for the image
        pref = "t{}p{}v{}".format(str(t).zfill(4), str(p).zfill(2), v)
        while True:
            collide = "." + str(uuid.uuid4())[:8]
            newName = "originalPages/" + pref + collide + ".png"
            if not os.path.isfile(newName):
                break

        with open(newName, "wb") as fh:
            fh.write(image)
        md5n = hashlib.md5(open(newName, "rb").read()).hexdigest()
        assert md5n == md5o

        val = self.DB.uploadKnownPage(t, p, v, fname, newName, md5n)
        print("Storing {} as {} = {}".format(pref, newName, val))


examDB = PlomDB()
spec = SpecParser().spec
peon = Server(spec, examDB)

try:
    # Run the server
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, ssl_context=sslContext, port=serverInfo["mport"])
except KeyboardInterrupt:
    pass
