import ast
from pathlib import Path
import re

status = ""


class StringPrinter(ast.NodeTransformer):
    """Prints all strings containing braces with some word-char in them"""
    def visit_Str(self, node):
        global status
        # note that this does not visit f-strings
        # note that it does not check that string has a trailing '.format'
        node_txt = node.s
        # look for braces with some word-char in them
        match = re.search(r"\{\s*\w+(.*?)\}", node_txt)
        if match:
            for x in match.groups():
                if "{" not in x:
                    status += f"{node.lineno}: {node_txt}\n"
        self.generic_visit(node)


for x in Path("./plom").glob("**/*.py"):
    with open(x, "r") as fh:
        tree = ast.parse(fh.read())
        status = ""
        StringPrinter().visit(tree)
        if status:
            print("*"*20)
            print(f"Checking '{x}'")
            print(status)
