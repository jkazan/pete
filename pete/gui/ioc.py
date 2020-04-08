import os

# import subprocess
import re

import epics
from epics import caget, caput
from PyQt5 import QtWidgets, QtGui

__author__ = "Johannes Kazantzidis"
__email__ = "johannes.kazantzidis@ess.eu"
__status__ = "Production"


def my_printf_handler(output_str):
    pass
    # TODO write output_str to some logfile


epics.ca.replace_printf_handler(my_printf_handler)


class IOCTree(QtWidgets.QTreeWidget):
    def __init__(self, pvlist, parent=None):
        super().__init__()
        self.pvlist = pvlist
        self.setup()

    def setup(self):
        self.setExpandsOnDoubleClick(True)
        self.setAnimated(True)
        self.setColumnCount(1)
        self.setHeaderLabel("IOC")
        root = None
        devices = {}
        topLevelItems = []
        try:
            lines = []
            if type(self.pvlist) is str:
                with open(self.pvlist) as f:
                    lines = f.readlines()
            else:
                lines = self.pvlist

            for line in lines:
                if line.endswith("\n") or line.endswith("\r"):
                    line = line[:-1]

                split_line = re.split(":", line)

                root = QtWidgets.QTreeWidgetItem([split_line[0]])

                if root.text(0) not in topLevelItems:
                    self.addTopLevelItem(root)
                    topLevelItems.append(root.text(0))

                root = self.topLevelItem(topLevelItems.index(root.text(0)))

                # Check if this is autosave stuff
                if split_line[0][-3:] == "-as":
                    field = split_line[1]
                    leaf = QtWidgets.QTreeWidgetItem([field])
                    root.addChild(leaf)
                    continue

                if len(split_line) > 2:
                    dev = split_line[1]
                    field = split_line[2]
                else:
                    dev = split_line[0]
                    field = split_line[1]

                if dev not in devices:
                    devices[dev] = QtWidgets.QTreeWidgetItem([dev])
                    root.addChild(devices[dev])

                leaf = QtWidgets.QTreeWidgetItem([field])
                devices[dev].addChild(leaf)

            self.sortItems(0, 0)

        except Exception as e:
            root = QtWidgets.QTreeWidgetItem([str(e)])
            self.addTopLevelItem(root)


class IOC(QtWidgets.QWidget):
    def __init__(self, pvlist, parent=None):
        super().__init__()
        self.tree = IOCTree(pvlist)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.sp = QtWidgets.QLineEdit()
        self.subject = QtWidgets.QLineEdit()
        self.feedback = QtWidgets.QLabel()
        self.dump_path = QtWidgets.QLineEdit()
        self.dump = QtWidgets.QPushButton("Dump Tree")

        self.setup()
        self.assignEvents()

    def setup(self):
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Setpoint and feedback
        spfb = QtWidgets.QWidget()
        spfb_hb = QtWidgets.QHBoxLayout(spfb)
        self.sp.setFixedWidth(120)
        self.feedback.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred
        )

        spfb_hb.addWidget(self.sp)
        spfb_hb.addWidget(self.feedback)
        spfb_hb.setContentsMargins(0, 0, 0, 0)

        # Dump tree path and button
        dt = QtWidgets.QWidget()
        dt_hb = QtWidgets.QHBoxLayout(dt)

        self.dump_path.setText(
            os.path.dirname(os.path.abspath(__file__)) + "/ioc_tree.txt"
        )

        dt_hb.addWidget(self.dump_path)
        self.dump.setFixedWidth(100)
        dt_hb.addWidget(self.dump)
        dt_hb.setContentsMargins(0, 0, 0, 0)

        # Add to layout
        self.layout.addWidget(self.subject)
        self.layout.addWidget(spfb)
        self.layout.addWidget(dt)
        self.layout.addWidget(self.tree)

    def assignEvents(self):
        self.sp.returnPressed.connect(self.applyVal)
        self.dump.clicked.connect(self.dumpData)
        self.tree.itemSelectionChanged.connect(self.setFeedback)

    def dumpData(self, root=None, indent=0, f=None):
        path = self.dump_path.text()
        if not os.path.isdir(os.path.dirname(path)):
            msg_box = QtWidgets.QMessageBox()
            msg_box.setStyleSheet(
                """
                        background-color: rgba(36, 70, 122, 255);
                        color: white;
                        """
            )
            msg_box.setFont(QtGui.QFont("Monospace", 10))
            msg_box.setIcon(QtWidgets.QMessageBox.Critical)
            msg_box.setText("No such directory:")
            msg_box.setInformativeText(os.path.dirname(path))
            msg_box.setWindowTitle("Bad path")
            msg_box.exec()
            return

        if f is None:  # If no file is open, open it
            with open(path, "w") as f:
                n_roots = self.tree.topLevelItemCount()
                for i in range(n_roots):
                    self.dumpData(self.tree.topLevelItem(i), 0, f)
        else:  # If file is open, get to work
            n_children = root.childCount()
            pv = self.getPV(root)
            val = self.getVal(pv)

            if val is None:
                val = ""
            else:
                val = str(val).replace("\n", "")
                val = ", " + val

            f.write(" " * indent + root.text(0) + val + "\n")

            for i in range(n_children):
                self.dumpData(root.child(i), indent + 4, f)

    def getPV(self, tree_item=None):
        if tree_item is None:
            tree_item = self.tree.currentItem()

        if tree_item is None or tree_item.childCount() != 0:  # Item is not a leaf
            return None

        family = []
        child = tree_item
        while child is not None:
            family.insert(0, child.text(0))
            child = child.parent()

        return ":".join(family)

    def getVal(self, pv):
        if pv is None:
            return ""
        self.subject.setText(pv)

        try:
            v = caget(pv)
            return v
        except Exception:
            return ""

    def setFeedback(self):
        pv = self.getPV()

        if pv is None:
            self.feedback.setText("")
        else:
            val = self.getVal(pv)
            val = str(val).replace("\n", "")
            self.feedback.setText(val)

    def applyVal(self):
        pv = self.getPV()
        if pv is not None:
            try:
                caput(pv, self.sp.text())
                self.setFeedback()
            except Exception as e:
                print(e)

    def setTheme(self, colors):
        self.tree.setStyleSheet(
            """
            QWidget{
                background-color: """
            + colors["tree"]
            + """;
                color: """
            + colors["font"]
            + """;
                border: 2px solid """
            + colors["border"]
            + """;
            }
            QHeaderView::section {
                background-color: """
            + colors["header"]
            + """;
                color: """
            + colors["font"]
            + """;
                alternate-background-color: transparent;
                border: none;
                font: monospace;
            }
            """
        )

        self.tree.header().setFont(QtGui.QFont("Monospace", 10, QtGui.QFont.Bold))
        self.tree.setFont(QtGui.QFont("Monospace", 10))
        self.tree.verticalScrollBar().setStyleSheet(
            """
                        QScrollBar:vertical {
                        border: none;
                        background: """
            + colors["border"]
            + """;
                        margin: 0px 0px 0px 0px;
                        }

                        QScrollBar::handle:vertical {
                        background: """
            + colors["scrollbar"]
            + """;
                        alternate-background-color: """
            + colors["scrollbar"]
            + """;
                        border: none;

                        }

                        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        border: none;
                        background: none;
                        }

                        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                        border: none;
                        background: none;
                        }
                        """
        )
        self.setStyleSheet("background-color: " + colors["window"] + ";")
        self.subject.setPlaceholderText("Command")
        self.subject.setFont(QtGui.QFont("Monospace", 10))
        self.subject.setStyleSheet(
            """
            color: """
            + colors["font"]
            + """;
            border: 2px solid """
            + colors["border"]
            + """;
            background-color: """
            + colors["edit"]
            + """;
            """
        )
        self.sp.setPlaceholderText("set value")
        self.sp.setFont(QtGui.QFont("Monospace", 10))
        self.sp.setStyleSheet(
            """
            color: """
            + colors["font"]
            + """;
            border: 2px solid """
            + colors["border"]
            + """;
            background-color: """
            + colors["edit"]
            + """;
            """
        )
        self.feedback.setFont(QtGui.QFont("Monospace", 10))
        self.feedback.setStyleSheet("color: " + colors["font"] + ";")
        self.dump.setFont(QtGui.QFont("Monospace", 10))
        self.dump.setStyleSheet("color: " + colors["font"] + ";")
        self.dump_path.setFont(QtGui.QFont("Monospace", 10))
        self.dump_path.setStyleSheet(
            """
            color: """
            + colors["font"]
            + """;
            border: 2px solid """
            + colors["border"]
            + """;
            background-color: """
            + colors["edit"]
            + """;
            """
        )
