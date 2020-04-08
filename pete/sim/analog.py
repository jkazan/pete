import time
import random

__author__ = "Johannes Kazantzidis"
__email__ = "johannes.kazantzidis@ess.eu"
__status__ = "Production"


class Analog(object):
    def __init__(self, client, node, val):
        """Initialize the device object.

        Args:
            client (OPCClient): OPCUA client connected to PLC.
            node (Node): OPCUA node of analog device.
            val (pair): Value pair between which values will be randomized.
        """
        self.client = client
        self.val = val
        self.node = node

    def run(self):
        """ Run infinite loop, updating with random values of device."""
        while True:
            value = random.randint(self.val[0], self.val[1])

            self.client.setValue(self.node, value)
            time.sleep(0.2)

    def get_name(self):
        """Returns name of Node"""
        return self.node.get_display_name().Text.split("_")[1]
