import os

from PyQt5 import QtWidgets, QtGui

from petenv.opc_client import OPCClient
from opcua import ua

__author__ = "Johannes Kazantzidis"
__email__ = "johannes.kazantzidis@ess.eu"
__status__ = "Production"


class PLCTree(QtWidgets.QTreeWidget):
    def __init__(self, client, parent=None):
        super().__init__()
        self.client = client
        self.setup()

    def setup(self):
        if self.client is None:
            root = QtWidgets.QTreeWidgetItem(["Could not connect to plc"])
        else:
            parent = self.client.get_root_node()
            root = QtWidgets.QTreeWidgetItem([self.client.getName(parent)])
            self.buildTree(root, parent)

        self.setExpandsOnDoubleClick(True)
        self.setAnimated(True)
        self.setColumnCount(1)
        self.setHeaderLabel("PLC")
        # self.header().hide()

        self.addTopLevelItem(root)

    def buildTree(self, branch, parent, level=0):
        children = parent.get_children()
        if not children:
            return

        for c in children:
            leaf = QtWidgets.QTreeWidgetItem([self.client.getName(c)])
            branch.addChild(leaf)

    def dumpData(self, path, root=None, indent=0, f=None, node=None):
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
                self.dumpData(path, root, 0, f)
        else:  # If file is open, get to work
            # First time dumpData is called, the node should be the root
            if root is None:
                root = self.topLevelItem(0)
                node = self.client.get_root_node()

            n_children = root.childCount()
            val = ""

            node_children = node.get_children()
            if not node_children:
                try:
                    val = ", " + str(node.get_value())
                    if len(val) > 30:
                        val = val[0:27] + "..."
                except Exception:
                    pass  # TODO: Do something here?

            f.write(" " * indent + root.text(0) + val + "\n")

            for i in range(n_children):
                self.dumpData(path, root.child(i), indent + 2, f, node_children[i])


class PLC(QtWidgets.QWidget):
    def __init__(self, ip, parent=None):
        super().__init__()
        self.client = OPCClient(ip)

        try:
            self.client.connect()
            self.tree = PLCTree(self.client)
            self.selected_node = self.client.get_root_node()
        except Exception:
            self.client = None
            self.tree = PLCTree(self.client)
            self.selected_node = None

        self.selected = self.tree.currentItem()
        self.sp = QtWidgets.QLineEdit()
        self.subject = QtWidgets.QLineEdit()
        self.feedback = QtWidgets.QLabel()
        self.dump_path = QtWidgets.QLineEdit()
        self.dump = QtWidgets.QPushButton("Dump Tree")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.setup()

        if self.client is not None:
            self.assignEvents()

    def setup(self):
        self.layout.setContentsMargins(0, 0, 0, 0)
        # Set point and feedback
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
            os.path.dirname(os.path.abspath(__file__)) + "/plc_tree.txt"
        )

        dt_hb.addWidget(self.dump_path)
        self.dump.setFixedWidth(100)
        dt_hb.addWidget(self.dump)
        dt_hb.setContentsMargins(0, 0, 0, 0)

        self.layout.addWidget(self.subject)
        self.layout.addWidget(spfb)
        self.layout.addWidget(dt)
        self.layout.addWidget(self.tree)

    def assignEvents(self):
        self.sp.returnPressed.connect(
            lambda: self.client.applyVal(
                self.selected_node, self.sp.text(), self.feedback
            )
        )

        self.dump.clicked.connect(lambda: self.tree.dumpData(self.dump_path.text()))
        self.tree.itemSelectionChanged.connect(self.evolveTree)

    def evolveTree(self):
        current = self.tree.currentItem()

        parents = []
        while current.text(0) != "0:Root":
            parents.insert(0, current.text(0))
            current = current.parent()

        command_str = "client.get_root_node()"
        node = self.client.get_root_node()

        if len(parents) > 0:
            command_str = command_str + ".get_child(" + str(parents) + ")"

        for p in parents:
            node = node.get_child(p)

        self.selected_node = node
        try:
            self.feedback.setText(str(node.get_value()))
        except Exception:
            pass  # No value

        self.subject.setText(command_str)
        self.subject.resize(self.tree.width(), self.subject.height())

        if parents in self.client.expand_list:
            return
        else:
            self.client.expand_list.append(parents)

        if not parents:
            return

        children = self.client.get_root_node().get_child(parents).get_children()
        branch = self.tree.currentItem()
        for c in children:
            leaf = QtWidgets.QTreeWidgetItem([self.client.getName(c)])
            branch.addChild(leaf)

    def disconnect(self):
        if self.client is not None:
            self.client.disconnect()

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

    def getPVs(self):
        objects = self.client.get_root_node().get_child("0:Objects").get_children()
        plc = objects[-1]  # Node for PLC
        instances = plc.get_child("3:DataBlocksInstance").get_children()

        pvs = []
        for node in instances:
            device = node.get_display_name().Text
            if "DEV_" in device and "_iDB" in device:
                dev_name = device.split("_")[1]
                inputs = []
                outputs = []
                try:
                    inputs = node.get_child("3:Inputs").get_children()
                    outputs = node.get_child("3:Outputs").get_children()
                except ua.uaerrors._auto.BadNoMatch:
                    pass

                for i in inputs:
                    pvs.append("{}:{}".format(dev_name, i.get_display_name().Text))
                for o in outputs:
                    pvs.append("{}:{}".format(dev_name, o.get_display_name().Text))

        return pvs
