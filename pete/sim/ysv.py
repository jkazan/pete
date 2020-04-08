import time

__author__ = "Johannes Kazantzidis"
__email__ = "johannes.kazantzidis@ess.eu"
__status__ = "Production"


class YSV(object):
    def __init__(self, client, energized_node, opened_node, closed_node):
        """Initialize the device object.

        Args:
            client (OPCClient): OPCUA client connected to PLC.
            energized_node (Node): OPCUA node of valve's 'energize' signal.
            opened_node (Node): OPCUA node of valve's 'opened' signal.
            closed_node (Node): OPCUA node of valve's 'closed' signal.
        """
        self.client = client
        self.energized_node = energized_node
        self.opened_node = opened_node
        self.closed_node = closed_node

    def run(self):
        """Run infinite loop, updating values of device.

        This simulator handles both valves that energize to open, and
        valves that energize to close.

        Caveat: PLC tag for energize signal must end with 'open' or
        'close', indicating the function of energizion.
        """
        oc = [self.opened_node, self.closed_node]  # Open/close nodes
        name = self.energized_node.get_display_name().Text  # 'energized' node name
        move_time = 0.7  # Time in seconds to open/close valve

        # Determine if energize to open or energize to close
        if "open" in name:
            et = 0  # Energize type is 'open'
        else:
            et = 1  # Energize type is 'close'

        # Infinite loop to check if energizeation is not matching the state of
        # the valve, remove current state, wait for simulated move time and set
        # new state.
        while True:
            if self.energized_node.get_value() and not oc[et].get_value():
                self.client.setValue(oc[1 - et], False)
                time.sleep(move_time)
                self.client.setValue(oc[et], True)

            if not self.energized_node.get_value() and not oc[1 - et].get_value():
                self.client.setValue(oc[et], False)
                time.sleep(move_time)
                self.client.setValue(oc[1 - et], True)

            time.sleep(0.2)

    def get_name(self):
        """Returns name of device"""
        return self.energized_node.get_display_name().Text.split("_")[1]
