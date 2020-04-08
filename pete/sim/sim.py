import argparse
import threading

from petenv.opc_client import OPCClient
from .analog import Analog
from .ysv import YSV
from .cv import CV

__author__ = "Johannes Kazantzidis"
__email__ = "johannes.kazantzidis@ess.eu"
__status__ = "Production"


class SimThread(threading.Thread):
    """Simulation thread"""

    def __init__(self, threadID, name, sim):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.sim = sim

    def run(self):
        print("Starting " + self.name)
        self.sim.run()
        print("Exiting " + self.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulator")
    parser.add_argument("ip", type=str, help="plc ip address")
    args = parser.parse_args()

    # Create and connect client
    client = OPCClient(args.ip)
    client.connect()

    # Get all TT, PT and RT nodes
    objects = client.get_root_node().get_child("0:Objects").get_children()
    plc = objects[-1]  # Node for PLC
    inputs = plc.get_child("3:Inputs")  # Node for plc inputs
    outputs = plc.get_child("3:Outputs")  # Node for plc outputs

    analog_tags = ["_TT-", "_PT-", "_RT-", "_FT"]  # Analog tags to look for
    analog_instruments = []  # List of analog nodes
    for node in inputs.get_children():
        node_name = node.get_display_name().Text  # Node name
        for tag in analog_tags:
            if tag in node_name and node_name not in analog_instruments:
                # Create simulator objects
                analog_instruments.append(Analog(client, node, (13000, 14000)))

    valves = []
    valve_tags = []
    for node in outputs.get_children():
        node_name = node.get_display_name().Text

        try:
            pid_tag = node_name.split("_")[1]  # P&ID tag

        except IndexError:
            continue

        if pid_tag in valve_tags:
            continue

        if "YSV" in node_name and node_name not in valves:
            e_node = outputs.get_child(node_name)  # 'energize'
            o_node = inputs.get_child("hwi_" + pid_tag + "_opened")  # 'opened'
            c_node = inputs.get_child("hwi_" + pid_tag + "_closed")  # 'closed'
            valves.append(YSV(client, e_node, o_node, c_node))
            valve_tags.append(pid_tag)
        elif "CV-" in node_name and node_name not in valves:
            o_node = outputs.get_child("hwo_" + pid_tag)  # 'open'
            i_node = inputs.get_child("hwi_" + pid_tag)  # 'openness'
            valves.append(CV(client, o_node, i_node))
            valve_tags.append(pid_tag)

    # Create and start threads
    for a in analog_instruments:
        SimThread(1, a.get_name(), a).start()

    for v in valves:
        SimThread(1, v.get_name(), v).start()
