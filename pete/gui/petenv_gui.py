import argparse
import os
import sys

from PyQt5 import QtWidgets, QtGui

from .plc import PLC
from .ioc import IOC

__author__ = "Johannes Kazantzidis"
__email__ = "johannes.kazantzidis@ess.eu"
__status__ = "Production"


class View(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.layout = QtWidgets.QHBoxLayout()

        self.initUI()

    def initUI(self):
        self.resize(1024, 768)
        self.setMinimumSize(800, 450)
        widget = QtWidgets.QWidget(self)
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)
        self.setWindowTitle("petenv")
        app_dir = os.path.dirname(os.path.realpath(__file__))
        self.setWindowIcon(QtGui.QIcon(app_dir + os.path.sep + "icon.png"))

    def addWidget(self, widget):
        self.layout.addWidget(widget)

    def setTheme(self, colors):
        self.setStyleSheet("background-color: " + colors["window"] + ";")


def main(ip, pvlist):
    # Preamble
    colors = {
        "window": "rgb(40, 40, 40)",
        "border": "rgb(36, 70, 122)",
        "font": "rgba(255, 255, 255, 230)",
        "edit": "rgba(36, 70, 122, 100)",
        "tree": "rgba(36, 70, 122, 100)",
        "scrollbar": "rgb(40, 40, 40)",
        "header": "rgb(36, 70, 122)",
    }

    app = QtWidgets.QApplication([])

    # Main window
    w = View()
    w.setTheme(colors)

    # PLC
    plc = PLC(ip)
    plc.setTheme(colors)
    app.aboutToQuit.connect(plc.disconnect)
    w.addWidget(plc)
    if not pvlist:
        pvlist = plc.getPVs()

    # IOC
    ioc = IOC(pvlist)
    ioc.setTheme(colors)
    w.addWidget(ioc)

    # Postamble
    w.show()

    sys.exit(app.exec_())


def run():
    parser = argparse.ArgumentParser(description="plc/epics gui")
    parser.add_argument("ip", type=str, help="plc ip address")
    parser.add_argument("-p", "--pvs", type=str, help="pv list")
    # parser.add_argument("pvs", type=str, help="path to pv list")
    args = parser.parse_args()
    main(args.ip, args.pvs)


if __name__ == "__main__":
    run()
