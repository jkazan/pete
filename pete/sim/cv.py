__author__ = "Johannes Kazantzidis"
__email__ = "johannes.kazantzidis@ess.eu"
__status__ = "Production"


class CV(object):
    def __init__(self, client, cmd_openness, fb_openness):
        """Initialize the device object.

        Args:
            client (OPCClient): OPCUA client connected to PLC.
            cmd_openness (Node): OPCUA node of valve's openness command in %.
            fb_openness (Node): OPCUA node of valve's openness feedback in %.
        """
        self.client = client
        self.cmd_openness = cmd_openness
        self.fb_openness = fb_openness

    def run(self):
        """ Run infinite loop, updating values of device."""
        while True:
            self.client.setValue(self.fb_openness, self.cmd_openness.get_value())

    def get_name(self):
        """Returns name of device"""
        return self.fb_openness.get_display_name().Text.split("_")[1]
