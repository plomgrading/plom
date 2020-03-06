from datetime import datetime


def printLog(who, msg):
    print(
        "[{} | {}] {}".format(datetime.now().strftime("%y:%m:%d-%H:%M:%S"), who, msg),
        flush=True,
    )
