import os
import sys
import tempfile
from shutil import copy
import subprocess

imgName = sys.argv[1]
curDir = os.getcwd()

with tempfile.TemporaryDirectory() as tmpDir:
    print("Processing file = {}".format(imgName))
    copy(imgName, tmpDir) #copy image to temp directory
    os.chdir(tmpDir) #move to temp directory

    # split image into five pieces, then extract qr codes from top and bottom.
    os.system('convert {} -crop 1x5@ tile_%d.png'.format(imgName))
    # now apply a slight blur filter to make reading codes easier
    os.system('mogrify tile_0.png -blur 0 -quality 100')
    os.system('mogrify tile_4.png -blur 0 -quality 100')
    try:
        up=subprocess.check_output(['zbarimg', '-q', '-Sdisable', '-Sqr.enable', 'tile_0.png']).decode().rstrip().split('\n')
    except subprocess.CalledProcessError as zberr:
        if(zberr.returncode==4): #means no codes found
            up=[]
        else:
            print("Zbarimg error processing file {}".format(imgName))
    try:
        down=subprocess.check_output(['zbarimg', '-q', '-Sdisable', '-Sqr.enable', 'tile_4.png']).decode().rstrip().split('\n')
    except subprocess.CalledProcessError as zberr:
        if(zberr.returncode==4): #means no codes found
            down=[]
        else:
            print("Zbarimg error processing file {}".format(imgName))
    both = set(up+down)
    print([up, down])
    # go back to original directory
    os.chdir(curDir)
    # dump the output of zbarimg
    with open('{}.qr'.format(imgName),'w') as fh:
        for X in both:
            fh.write('{}\n'.format(X))
    # there should be 1 qr code in top half and 2 in bottom half
    # if not then flip the image.
    if(len(up)>len(down)):
        os.system('mogrify -rotate 180 {}'.format(imgName))
