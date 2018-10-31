import sys
from mlp_useful import SimpleCommentTable
from PyQt5.QtWidgets import QApplication, QGridLayout, QWidget


class tmp(QWidget):
    def __init__(self):
        super(tmp, self).__init__()
        self.tab = SimpleCommentTable(self)
        grid = QGridLayout()
        grid.addWidget(self.tab,1,1)
        self.setLayout(grid)
        self.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # app.setStyle(QStyleFactory.create("Fusion"))
    argh = tmp()
    sys.exit(app.exec_())
