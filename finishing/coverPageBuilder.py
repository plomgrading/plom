import sys
from weasyprint import HTML, CSS

arg = eval(sys.argv[1])

css = CSS(string='''
body {
    font-family: sans serif;
}
table, th, td {
    border: 1px solid black;
    border-collapse: collapse;
    padding: 5px;
    text-align: center;
}
''')

htmlText = "<h3>Results</h3>\n"
htmlText += "<ul>"
htmlText += "<li>Name = {}</li>\n".format(arg[1])
htmlText += "<li>ID = {}</li>\n".format(arg[2])
htmlText += "<li>Test number = {}</li>\n".format(arg[0])
htmlText += "</ul>"
htmlText += "<table>\n"
htmlText += "<tr><th>question</th><th>version</th><th>mark</th><th>out of</th></tr>\n"
totalMark = 0
maxPossible = 0
for x in range(3,len(arg)):
    y = arg[x]
    totalMark += y[2]
    maxPossible += y[3]
    htmlText += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>\n".format(y[0],y[1],y[2],y[3])
htmlText += "<tr><td>total</td><td>{}</td><td>{}</td><td>&middot;</td>\n".format(totalMark, maxPossible)
htmlText += "</table>\n"

cover = HTML(string=htmlText)
cover.write_pdf("coverPages/cover_{}.pdf".format(str(arg[0]).zfill(4)), stylesheets=[css])
