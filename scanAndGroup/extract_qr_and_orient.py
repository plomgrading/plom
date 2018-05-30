import os
import sys
import tempfile
from shutil import copy
import subprocess

imgName = sys.argv[1]
curDir = os.getcwd()

with tempfile.TemporaryDirectory() as tmpDir:
    copy(imgName, tmpDir) #copy image to temp directory
    os.chdir(tmpDir) #move to temp directory

    # split image into top and bottom halves, then extract qr codes from each.
    os.system('convert {} -crop 1x2@ tile_%d.png'.format(imgName))
    up=subprocess.check_output(['zbarimg', '-q', 'tile_0.png']).decode().rstrip().split('\n')
    down=subprocess.check_output(['zbarimg', '-q', 'tile_1.png']).decode().rstrip().split('\n')
    both = set(up+down)
    # go back to original directory
    os.chdir(curDir)
    # dump the output of zbarimg
    with open('{}.qr'.format(imgName),'w') as fh:
        for X in both:
            fh.write('{}\n'.format(X))
    # there should be 1 qr code in top half and 2 in bottom half
    # if not then flip the image.
    if(len(up)>len(down)):
        os.system('mogrify mogrify -rotate 180 {}',imgName)
