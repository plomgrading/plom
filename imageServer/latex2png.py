import os
import sys
import subprocess
import tempfile

head = """
\\documentclass[12pt]{article}
\\usepackage[letterpaper, textwidth=5in]{geometry}
\\usepackage{amsmath, amsfonts}
\\usepackage{xcolor}
\\usepackage[active, tightpage]{preview}
\\begin{document}
\\begin{preview}
\\color{red}
"""

foot = """
\\end{preview}
\\end{document}
"""

cdir = os.getcwd()
td = tempfile.TemporaryDirectory()
os.chdir(td.name)

frag = ""
with open(sys.argv[1], "r") as fh:
    frag = fh.read()

with open("frag.tex".format(td.name), "w") as fh:
    fh.write(head)
    fh.write(frag)
    fh.write(foot)

texit = subprocess.run(
    ["latex", "-interaction=nonstopmode", "-no-shell-escape", "frag.tex"]
)
if texit.returncode != 0:
    sys.exit(textit.returncode)

convit = subprocess.run(
    ["dvipng", "-q", "-D", "225", "-bg", "transparent", "frag.dvi", "-o" "frag.png"]
)
if convit.returncode != 0:
    sys.exit(convit.returncode)

os.system("cp frag.png {}".format(sys.argv[2]))
os.chdir(cdir)
