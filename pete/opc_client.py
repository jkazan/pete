from opcua import Client
from opcua import ua

__author__ = "Johannes Kazantzidis"
__email__ = "johannes.kazantzidis@ess.eu"
__status__ = "Production"


class OPCClient(Client):
    def __init__(self, ip, timeout=4):
        """Initialize OPCUA client.

        Args:
            ip (str): PLC IP address.
            timeout (float): Timeout in seconds for connection.
        """
        url = "opc.tcp://{}:4840".format(ip)
        super().__init__(url, timeout=4)
        self.expand_list = []
        self.selected = self.get_root_node()

    def setValue(self, node, value):
        """Set value to OPCUA node."""
        variant_type = node.get_data_type_as_variant_type()
        variant = ua.uatypes.Variant(value, variant_type)
        data_value = ua.DataValue()
        data_value.Value = variant
        node.set_data_value(data_value, variant_type)

    def getValue(self, node):
        """Return node value.

        This function merely translates opcua package's 'get_value' to a
        syntax following this class. This is needed as the 'setValue'
        method differs from the opcua package's node function
        'set_value'.
        """
        return node.get_value()

    def getName(self, node):
        """Returns name of node"""
        return str(node.get_browse_name()).split("(")[1].split(")")[0]

    def applyVal(self, node, val, feedback):
        """Value setter including error handling.

        This function is mainly used by the petenv gui.
        """
        try:
            self.setValue(node, type(node.get_value())(val))
            feedback.setText(str(node.get_value()))
        except Exception as e:
            print(e)
            print("Couldn't set value")
