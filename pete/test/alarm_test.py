import logging
import time

from petenv.opc_client import OPCClient
import pytest

from epics import ca, caget, caput

__author__ = "Johannes Kazantzidis"
__email__ = "johannes.kazantzidis@ess.eu"
__status__ = "Production"

QUIET = True
IP = input("\n\nPLC IP: ")  # Hardcode your IP here to avoid question


def quiet_mode(msg_bytes):
    """Quench pyepics warnings

    When running over VPN, two networks are enabled. The client library will
    find the PV on the same IOC twice, from different IP addresses. This ambiguity
    results in the following warning:

    CA.Client.Exception...............................................
        Warning: "Identical process variable names on multiple servers"
        Context: "Channel: "Tgt-HeIn1013:Proc-YSV-033:ClosingTime",
        Connecting to: L480:35519, Ignored: L480:35519"
        Source File: ../cac.cpp line 1320
        Current Time: Fri Mar 20 2020 10:51:04.209830858
    ..................................................................

    As this is no problem for this test, this function serves the
    purpose to quench such warnings in order to not clutter the pytest
    terminal output.
    """
    pass  # Alternatively, we could write the warnings into a log file.


if QUIET:
    ca.replace_printf_handler(quiet_mode)  # Replace pyepics handler


@pytest.fixture(scope="module")
def com():
    """Setup OPCUA client.

    Create OPCUA client and connect to PLC upon starting test. When the
    test is finished, disconnect the client.
    """
    # Connect to opcua server
    client = OPCClient(IP)
    client.connect()

    # Get the plc node
    objects = client.get_root_node().get_child("0:Objects").get_children()
    plc = objects[-1]  # Node for PLC

    # Provide the fixture value. Eferything after this is teardown code
    yield client, plc
    client.disconnect()


def wait(pv, value, timeout=4.0):
    """Wait for PV value.

    Run `caget` on a PV until expected value is seen, or until timeout.

    Args:
        pv (str): EPICS PV name
        value (float): Expected PV value
        timeout (float): Timeout in seconds
    """
    t = 0
    delay = 0.2
    while caget(pv) != value:
        t += 1
        time.sleep(delay)
        if t > timeout / delay:
            break


def get_analogs():
    """Return list of all analog transmitter PV names.

    Note that this function searches for devices with 'T-' in it. If
    found, petenv assumes it's a transmitter. If this is not always the
    case, this function must be modified.
    """
    # Connect to opcua server (this function cannot use the fixture)
    client = OPCClient(IP)
    client.connect()

    # Get the plc node
    objects = client.get_root_node().get_child("0:Objects").get_children()
    plc = objects[-1]  # Node for PLC

    # Find all analog transmitters
    transmitters = []
    instances = plc.get_child("3:DataBlocksInstance").get_children()
    for node in instances:
        node_name = node.get_display_name().Text
        if (
            "_iDB" in node_name
            and node_name not in transmitters
            and ("T-" in node_name or "E-" in node_name)
        ):
            transmitters.append(node_name.split("_")[1])  # P&ID tag

    # Disconnect from opcua server
    client.disconnect()

    return transmitters


def get_valves():
    """Return list of all YSV valves PV names.

    Note that this function is programmed to only search for valves
    called 'YSV'. Consider adding more names if needed.
    """
    # Connect to opcua server (this function cannot use the fixture)
    client = OPCClient(IP)
    client.connect()

    # Get the plc node
    objects = client.get_root_node().get_child("0:Objects").get_children()
    plc = objects[-1]  # Node for PLC

    # Find all YSV valves
    valves = []
    instances = plc.get_child("3:DataBlocksInstance").get_children()
    for node in instances:
        node_name = node.get_display_name().Text
        if "YSV" in node_name and "_iDB" in node_name and node_name not in valves:
            valves.append(node_name.split("_")[1])  # P&ID tag

    # Disconnect from the opcua server
    client.disconnect()

    return valves


# @pytest.mark.skip(reason="just wanna test valves now")
@pytest.mark.parametrize("pv", get_analogs())
def test_transmitter_alarms(com, pv):
    """Verify analog transmitter alarms.

    Verify HIHI, HI, LO, LOLO, Overrange and Underrange signals

    Args:
        com (tuple(OPCClient, opcua.common.node.Node)): OPCUA client, plc node
        pv (str): PV name of transmitter to be tested
    """
    logger = logging.getLogger()
    client = com[0]
    plc = com[1]
    caput("{}:Cmd_FreeRun".format(pv), 1)
    pid_tag = "{}-{}".format(pv.split("-")[-2], pv.split("-")[-1])

    # Find input signal name
    ai = None
    for i in plc.get_child("3:Inputs").get_children():
        if pid_tag in i.get_display_name().Text:
            pid_tag
            ai = i
            break

    scale_low = caget("{}:ScaleLOW".format(pv))
    scale_high = caget("{}:ScaleHIGH".format(pv))
    ciel = 27648
    offset = 10
    hihi_lim = caget("{}:FB_Limit_HIHI".format(pv))
    hi_lim = caget("{}:FB_Limit_HI".format(pv))
    lo_lim = caget("{}:FB_Limit_LO".format(pv))
    lolo_lim = caget("{}:FB_Limit_LOLO".format(pv))
    delay = 1
    logger.warning("HIHI limit: {}\n".format(hihi_lim))
    logger.warning("HI limit: {}\n".format(hi_lim))
    logger.warning("LOLO limit: {}\n".format(lo_lim))
    logger.warning("LO limit: {}\n".format(lolo_lim))

    # Test overrange and io error
    client.setValue(ai, 30000)
    time.sleep(delay)
    assert caget("{}:Overrange".format(pv)) == 1
    assert caget("{}:IO_Error".format(pv)) == 1

    # Test underrange and io error
    client.setValue(ai, -1)
    time.sleep(delay)
    assert caget("{}:Underrange".format(pv)) == 1
    assert caget("{}:IO_Error".format(pv)) == 1

    # Test HIHI alarm
    if hihi_lim != scale_high:
        hihi = ciel * (hihi_lim - scale_low) / (scale_high - scale_low) + offset
        client.setValue(ai, int(hihi))
        wait("{}:HIHI".format(pv), 1)
        assert caget("{}:HIHI".format(pv)) == 1

    # Test HI alarm
    if hi_lim != scale_high:
        hi = ciel * (hi_lim - scale_low) / (scale_high - scale_low) + offset
        client.setValue(ai, int(hi))
        wait("{}:HI".format(pv), 1)
        assert caget("{}:HI".format(pv)) == 1

    # Test LO alarm
    if lo_lim != scale_low:
        lo = ciel * (lo_lim - scale_low) / (scale_high - scale_low) - offset
        client.setValue(ai, int(lo))
        wait("{}:LO".format(pv), 1)
        assert caget("{}:LO".format(pv)) == 1

    # Test LOLO alarm
    if lolo_lim != scale_low:
        lolo = ciel * (lolo_lim - scale_low) / (scale_high - scale_low) - offset
        client.setValue(ai, int(lolo))
        wait("{}:LOLO".format(pv), 1)
        assert caget("{}:LOLO".format(pv)) == 1

    # Check if values seem to be unset
    if hihi_lim == 0 and hi_lim == 0 and lo_lim == 0 and lolo_lim == 0:
        msg = "The limits for this device do not seem to be configured. "
        msg += "All limits are currently set to 0."
        print(msg)

    # Set non-alarming value
    nominal_lim = lo_lim + (hi_lim - lo_lim) / 2
    nominal = ciel * (nominal_lim - scale_low) / (scale_high - scale_low)
    client.setValue(ai, int(nominal))  # Set a value that is not an alarm


# @pytest.mark.skip(reason="just wanna test transmitters now")
@pytest.mark.parametrize("pv", get_valves())
def test_pv_valve_alarms(com, pv):
    """Verify solenoid valve alarms.

    Verify that opening timeout, closing timeout and IO error is working
    properly. Note that IO error is true if the valves 'opened' and
    'closed' signals are simultaneously true.

    Args:
        com (tuple(OPCClient, opcua.common.node.Node)): OPCUA client, plc node
        pv (str): PV name of valve to be tested
    """
    client = com[0]
    plc = com[1]

    pid_tag = "{}-{}".format(pv.split("-")[-2], pv.split("-")[-1])
    caput("{}:Cmd_Force".format(pv), 1)
    inputs = plc.get_child("3:Inputs")
    opened = inputs.get_child("3:hwi_{}_opened".format(pid_tag))
    closed = inputs.get_child("3:hwi_{}_closed".format(pid_tag))

    close_pv = "{}:Cmd_ForceClose".format(pv)
    open_pv = "{}:Cmd_ForceOpen".format(pv)
    opening_time = caget("{}:ClosingTime".format(pv)) / 1000 + 2  # ms to s + offset
    closing_time = caget("{}:ClosingTime".format(pv)) / 1000 + 2  # ms to s + offset
    opening_timeout_pv = "{}:Opening_TimeOut".format(pv)
    closing_timeout_pv = "{}:Closing_TimeOut".format(pv)

    # Close valve and remove any prevailing alarm
    caput(close_pv, 1)
    client.setValue(closed, True)
    client.setValue(opened, False)
    wait("{}:Closed".format(pv), 1)
    wait("{}:Opened".format(pv), 0)
    caput("{}:Cmd_AckAlarm".format(pv), 1)

    wait("{}:GroupAlarm".format(pv), 0)
    assert caget("{}:GroupAlarm".format(pv)) == 0

    # Run both open and close actions, and check timeouts on each
    caput(open_pv, 1)  # Command open
    time.sleep(opening_time)  # Wait until opening timeout
    assert caget(opening_timeout_pv) == 1  # Verify timeout alarm
    client.setValue(closed, False)  # Remove closed signal
    client.setValue(opened, True)  # Set opened signal
    wait("{}:Opened".format(pv), 1)  # Wait for new state to take effect
    wait("{}:Closed".format(pv), 0)  # Wait for new state to take effect
    caput("{}:Cmd_AckAlarm".format(pv), 1)  # Acknowledge alarm

    caput(close_pv, 1)  # Command close
    time.sleep(closing_time)  # Wait until closing timeout
    assert caget(closing_timeout_pv) == 1  # Verify timeout alarm
    client.setValue(closed, True)  # Set closed signal
    client.setValue(opened, False)  # Remove opened signal
    wait("{}:Opened".format(pv), 0)  # Wait for new state to take effect
    wait("{}:Closed".format(pv), 1)  # Wait for new state to take effect
    caput("{}:Cmd_AckAlarm".format(pv), 1)  # Acknowledge alarm

    # Verify alarm if both 'opened' and 'closed' signals are prevailing
    client.setValue(closed, True)
    client.setValue(opened, True)
    wait("{}:Opened".format(pv), 1)
    wait("{}:Closed".format(pv), 1)
    assert caget("{}:IO_Error".format(pv)) == 1

    # Close valve and remove any prevailing alarm
    caput(close_pv, 1)
    client.setValue(closed, True)
    client.setValue(opened, False)
    wait("{}:Opened".format(pv), 0)  # Wait for new state to take effect
    wait("{}:Closed".format(pv), 1)  # Wait for new state to take effect
    caput("{}:Cmd_AckAlarm".format(pv), 1)
    wait("{}:GroupAlarm".format(pv), 0)
    assert caget("{}:GroupAlarm".format(pv)) == 0
