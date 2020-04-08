# This script is a full functional test for the THCCS circulator system. This
# script serves as a reference for when you are starting to get used to writing
# test scripts. Please go to the respective web pages for pytest for more
# information on features.

import inspect
import sys
import time

from petenv.opc_client import OPCClient
import pytest

from epics import ca, caget, caput

QUIET = True
VERBOSE = False


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

primary = [1, 0]
order = [("a", "b"), ("b", "a")]
MIN_RPM = 10000


def DEBUG(msg):
    """Returns the current line number in our program."""
    if VERBOSE:
        print("line {}: {}".format(inspect.currentframe().f_back.f_lineno, msg))


@pytest.fixture(scope="module")
def client():
    """Setup OPCUA client.

    Create OPCUA client and connect to PLC upon starting test. When the
    test is finished, disconnect the client.
    """
    c = OPCClient("172.30.4.163")
    c.connect()

    yield c  # Provide the fixture value. Eferything after this is teardown code
    sys.stdout.write("\nteardown client")
    init()
    c.disconnect()


# @pytest.mark.skip(reason="already works")
@pytest.mark.parametrize("prim, sec", order, ids=["V-001a", "V-001b"])
def test_circulator_startup_sequence(client, prim, sec):
    """Verify single circulator startup sequence.

    Go to RUNNING with beam power = 0, implying that only the primary
    circulator shall start. Run test with each circulator as primary.

    Args:
        client (OPCClient): OPCUA client
        prim (int): Indicating which circulator is primary (1=A, 0=B)
    """

    init()
    DEBUG("Set beam power to 0")
    set_beam_power(client, 0)
    DEBUG("Set circulator {} to primary".format(prim))
    caput("Tgt-HeC1010:Proc-V-001a:P_Primary", int(prim == "a"))
    caput("Tgt-HeC1010:Proc-V-001b:P_Primary", int(prim == "b"))
    wait("Tgt-HeC1010:Proc-V-001a:P_Primary", int(prim == "a"))
    wait("Tgt-HeC1010:Proc-V-001b:P_Primary", int(prim == "b"))
    assert caget("Tgt-HeC1010:Proc-V-001a:P_Primary") == int(prim == "a")
    assert caget("Tgt-HeC1010:Proc-V-001b:P_Primary") == int(prim == "b")

    DEBUG("Go to starting")
    caput("Tgt-HeC1010:Ctrl-PLC-001:P_State", 200)  # Request STARTING

    # Check that no circulator, nor the secondary valve, starts/opens while the
    # primary valve has not yet opened
    DEBUG(
        "Asserting that circulator {} has not started as valve is still closed".format(
            prim
        )
    )
    DEBUG("Asserting that circulator {} has not started".format(sec))
    DEBUG("Asserting that valve {} is closed".format(sec))
    t = 0.0
    while caget("Tgt-HeC1010:Proc-YSV-005{}:Opened".format(prim)) == 0:
        assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim)) == 0
        assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec)) == 0
        assert caget("Tgt-HeC1010:Proc-YSV-005{}:Closed".format(sec)) == 1
        time.sleep(0.2)
        t += 0.5
        if t > 30:
            break

    # Check that while primary circulator is starting, secondary circulator is
    # still off, primary valve stays open and secondary valve stays closed
    while caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim)) != 2:
        assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec)) == 0
        assert caget("Tgt-HeC1010:Proc-YSV-005{}:Opened".format(prim)) == 1
        assert caget("Tgt-HeC1010:Proc-YSV-005{}:Closed".format(sec)) == 1
        time.sleep(0.2)

    # Check that primary circulator is running, secondary circulator is
    # still off, primary valve stays open and secondary valve stays closed
    DEBUG("Assert that primary circulator is running")
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim)) == 2
    DEBUG("Assert that secondary circulator is still off")
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec)) == 0
    DEBUG("Assert that primary valve is still open")
    assert caget("Tgt-HeC1010:Proc-YSV-005{}:Opened".format(prim)) == 1
    DEBUG("Assert that secondary valve is still closed")
    assert caget("Tgt-HeC1010:Proc-YSV-005{}:Closed".format(sec)) == 1


# @pytest.mark.skip(reason="already works")
def test_double_circulator_startup_sequence(client):
    """Verify double circulator startup sequence.

    Go to RUNNING with beam power = 3, implying that both circulators
    shall start.

    Args:
        client (OPCClient): OPCUA client
    """
    init()

    DEBUG("Verify that both circulators are in operational state off")
    assert caget("Tgt-HeC1010:Proc-V-001a:OpState") == 0
    assert caget("Tgt-HeC1010:Proc-V-001b:OpState") == 0

    DEBUG("Set beam power to 3 MW")
    set_beam_power(client, 3)

    DEBUG("Go to starting")
    caput("Tgt-HeC1010:Ctrl-PLC-001:P_State", 200)  # Request STARTING

    wait("Tgt-HeC1010:Proc-V-001a:OpState", 2)
    wait("Tgt-HeC1010:Proc-V-001b:OpState", 2)

    assert caget("Tgt-HeC1010:Proc-V-001a:OpState") == 2
    assert caget("Tgt-HeC1010:Proc-V-001b:OpState") == 2


# @pytest.mark.skip(reason="already works")
@pytest.mark.parametrize("prim, sec", order, ids=["A to B", "B to A"])
def test_switch_circulator(client, prim, sec):
    """Switch circulator.

    This tests the feature of switching the running circulator to the
    other, when only one is running.

    Args:
        client (OPCClient): OPCUA client
        prim (int): Indicating which circulator is primary (1=A, 0=B)
    """
    init()
    DEBUG("Verify that both circulators are in operational state off")
    assert caget("Tgt-HeC1010:Proc-V-001a:OpState") == 0
    assert caget("Tgt-HeC1010:Proc-V-001b:OpState") == 0

    DEBUG("setting bp to 0")
    set_beam_power(client, 0)
    time.sleep(2)  # wait for beam power to take effect. This is on PLC level.

    DEBUG("Set circulator {} to primary".format(prim))
    caput("Tgt-HeC1010:Proc-V-001a:P_Primary", int(prim == "a"))
    caput("Tgt-HeC1010:Proc-V-001b:P_Primary", int(prim == "b"))
    wait("Tgt-HeC1010:Proc-V-001a:P_Primary", int(prim == "a"))
    wait("Tgt-HeC1010:Proc-V-001b:P_Primary", int(prim == "b"))
    assert caget("Tgt-HeC1010:Proc-V-001a:P_Primary") == int(prim == "a")
    assert caget("Tgt-HeC1010:Proc-V-001b:P_Primary") == int(prim == "b")

    DEBUG("Go to starting")
    caput("Tgt-HeC1010:Ctrl-PLC-001:P_State", 200)  # Request STARTING
    wait("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim), 2)

    DEBUG("assert that V-001{} is running and V-001{} is off".format(prim, sec))
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim)) == 2
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec)) == 0

    DEBUG("Wait 5 seconds and verify that nothing changed")
    time.sleep(5)
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim)) == 2
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec)) == 0

    DEBUG("Set circulator {} to primary".format(sec))
    caput("Tgt-HeC1010:Proc-V-001a:P_Primary", int(sec == "a"))
    caput("Tgt-HeC1010:Proc-V-001b:P_Primary", int(sec == "b"))
    wait("Tgt-HeC1010:Proc-V-001a:P_Primary", int(sec == "a"))
    wait("Tgt-HeC1010:Proc-V-001b:P_Primary", int(sec == "b"))
    assert caget("Tgt-HeC1010:Proc-V-001a:P_Primary") == int(sec == "a")
    assert caget("Tgt-HeC1010:Proc-V-001b:P_Primary") == int(sec == "b")

    DEBUG("Wait for circulators to switch and assert switch went well")
    wait("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim), 0)
    wait("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec), 2)
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim)) == 0
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec)) == 2


# @pytest.mark.skip(reason="already works")
@pytest.mark.parametrize("prim, sec", order, ids=["A to AB", "B to AB"])
def test_1to2(client, prim, sec):
    """Go from running one, to running two, circulators.

    This verifies that the system starts up the secondary circulator if
    the flow increases to above the threshold for running both.

    Args:
        client (OPCClient): OPCUA client
        prim (int): Indicating which circulator is primary (1=A, 0=B)
    """
    init()

    DEBUG("Verify that both circulators are in operational state off")
    assert caget("Tgt-HeC1010:Proc-V-001a:OpState") == 0
    assert caget("Tgt-HeC1010:Proc-V-001b:OpState") == 0

    DEBUG("setting bp to 1.7 MW")
    set_beam_power(client, 1.7)
    time.sleep(2)  # wait for beam power to take effect. This is on PLC level.

    DEBUG("Set circulator {} to primary".format(prim))
    caput("Tgt-HeC1010:Proc-V-001a:P_Primary", int(prim == "a"))
    caput("Tgt-HeC1010:Proc-V-001b:P_Primary", int(prim == "b"))
    wait("Tgt-HeC1010:Proc-V-001a:P_Primary", int(prim == "a"))
    wait("Tgt-HeC1010:Proc-V-001b:P_Primary", int(prim == "b"))
    assert caget("Tgt-HeC1010:Proc-V-001a:P_Primary") == int(prim == "a")
    assert caget("Tgt-HeC1010:Proc-V-001b:P_Primary") == int(prim == "b")

    DEBUG("Go to starting")
    caput("Tgt-HeC1010:Ctrl-PLC-001:P_State", 200)  # Request STARTING
    wait("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim), 2)

    DEBUG("Assert that primary circulator is running and secondary off")
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim)) == 2
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec)) == 0

    DEBUG("setting bp to 3 MW")
    set_beam_power(client, 3)
    time.sleep(2)  # wait for beam power to take effect. This is on PLC level.

    DEBUG("Assert that both circulators are running")
    wait("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim), 2)
    wait("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec), 2)
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim)) == 2
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec)) == 2


# @pytest.mark.skip(reason="already works")
@pytest.mark.parametrize("prim, sec", order, ids=["AB to A", "AB to B"])
def test_2to1(client, prim, sec):
    """Go from running two, to running one, circulator.

    This verifies that the system shutsdown the secondary circulator if
    the flow decreases to below the threshold for running both.

    Args:
        client (OPCClient): OPCUA client
        prim (int): Indicating which circulator is primary (1=A, 0=B)
    """
    init()

    DEBUG("Verify that both circulators are in operational state off")
    assert caget("Tgt-HeC1010:Proc-V-001a:OpState") == 0
    assert caget("Tgt-HeC1010:Proc-V-001b:OpState") == 0

    DEBUG("setting bp to 3 MW")
    set_beam_power(client, 3)
    time.sleep(2)  # wait for beam power to take effect. This is on PLC level.

    DEBUG("Set circulator {} to primary".format(prim))
    caput("Tgt-HeC1010:Proc-V-001a:P_Primary", int(prim == "a"))
    caput("Tgt-HeC1010:Proc-V-001b:P_Primary", int(prim == "b"))
    wait("Tgt-HeC1010:Proc-V-001a:P_Primary", int(prim == "a"))
    wait("Tgt-HeC1010:Proc-V-001b:P_Primary", int(prim == "b"))
    assert caget("Tgt-HeC1010:Proc-V-001a:P_Primary") == int(prim == "a")
    assert caget("Tgt-HeC1010:Proc-V-001b:P_Primary") == int(prim == "b")

    DEBUG("Go to starting")
    caput("Tgt-HeC1010:Ctrl-PLC-001:P_State", 200)  # Request STARTING
    wait("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim), 2)
    wait("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec), 2)

    DEBUG("Assert that both circulators are running")
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim)) == 2
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec)) == 2

    DEBUG("setting bp to 1.7 MW")
    set_beam_power(client, 1.7)
    time.sleep(2)  # wait for beam power to take effect. This is on PLC level.

    DEBUG("Wait for secondary to shut down")
    wait("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec), 0)

    DEBUG("Wait for primary to go back to running")
    wait("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim), 2)

    DEBUG("Assert that both circulators are running")
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(prim)) == 2
    assert caget("Tgt-HeC1010:Proc-V-001{}:OpState".format(sec)) == 0


def set_beam_power(client, bp):
    """ Sets beam power.

    Args:
        client (OPCClient): OPCUA client
        bp (float): Beam power
    """
    node = client.get_root_node().get_child(
        [
            "0:Objects",
            "3:THCCS_PLC",
            "3:DataBlocksGlobal",
            "3:external_signals",
            "3:beam_power_mw",
        ]
    )

    client.setValue(node, bp)


def wait(pv, value, timeout=30.0):
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


def init():
    """Initialize test.

    This method serves the purpose of stopping the system, and is called
    from multiple test functions.
    """
    DEBUG("Initialize test")
    if caget("Tgt-HeC1010:Ctrl-PLC-001:FB_State") == 500:
        DEBUG("Set all to manual")
        if caget("Tgt-HeC1010:Proc-V-001a:OpMode_Manual") != 1:
            caput("Tgt-HeC1010:Proc-V-001a:Cmd_Manual", 1)
            wait("Tgt-HeC1010:Proc-V-001a:OpMode_Manual", 1)
        if caget("Tgt-HeC1010:Proc-V-001b:OpMode_Manual") != 1:
            caput("Tgt-HeC1010:Proc-V-001b:Cmd_Manual", 1)
            wait("Tgt-HeC1010:Proc-V-001b:OpMode_Manual", 1)
        if caget("Tgt-HeC1010:Proc-YSV-005a:OpMode_Manual") != 1:
            caput("Tgt-HeC1010:Proc-YSV-005a:Cmd_Manual", 1)
            wait("Tgt-HeC1010:Proc-YSV-005a:OpMode_Manual", 1)
        if caget("Tgt-HeC1010:Proc-YSV-005b:OpMode_Manual") != 1:
            caput("Tgt-HeC1010:Proc-YSV-005b:Cmd_Manual", 1)
            wait("Tgt-HeC1010:Proc-YSV-005b:OpMode_Manual", 1)

        DEBUG("Shutdown circulators")
        if caget("Tgt-HeC1010:Proc-V-001a:OpState") != 0:
            DEBUG("Go to min rpm")
            caput("Tgt-HeC1010:Proc-V-001a:P_Setpoint", MIN_RPM)
            wait("Tgt-HeC1010:Proc-V-001a:Speed", MIN_RPM)
            DEBUG("Stop circulator")
            caput("Tgt-HeC1010:Proc-V-001a:Cmd_Stop", 1)
            wait("Tgt-HeC1010:Proc-V-001a:OpState", 0)
        if caget("Tgt-HeC1010:Proc-V-001b:OpState") != 0:
            DEBUG("Go to min rpm")
            DEBUG("TEST1")
            caput("Tgt-HeC1010:Proc-V-001a:P_Setpoint", MIN_RPM)
            DEBUG("TEST2")
            wait("Tgt-HeC1010:Proc-V-001b:Speed", MIN_RPM)
            DEBUG("TEST3")
            DEBUG("Stop circulator")
            caput("Tgt-HeC1010:Proc-V-001b:Cmd_Stop", 1)
            wait("Tgt-HeC1010:Proc-V-001b:OpState", 0)

        DEBUG("Close valves")
        if caget("Tgt-HeC1010:Proc-YSV-005a:Closed") != 1:
            caput("Tgt-HeC1010:Proc-YSV-005a:Cmd_ManuClose", 1)
            wait("Tgt-HeC1010:Proc-YSV-005a:Closed", 1)
        if caget("Tgt-HeC1010:Proc-YSV-005b:Closed") != 1:
            caput("Tgt-HeC1010:Proc-YSV-005b:Cmd_ManuClose", 1)
            wait("Tgt-HeC1010:Proc-YSV-005b:Closed", 1)

        DEBUG("Go to off")
        caput("Tgt-HeC1010:Ctrl-PLC-001:P_State", 0)
        wait("Tgt-HeC1010:Ctrl-PLC-001:FB_State", 0)

        DEBUG("Set all to auto mode")
        if caget("Tgt-HeC1010:Proc-V-001a:OpMode_Auto") != 1:
            caput("Tgt-HeC1010:Proc-V-001a:Cmd_Auto", 1)
            wait("Tgt-HeC1010:Proc-V-001a:OpMode_Auto", 1)
        if caget("Tgt-HeC1010:Proc-V-001b:OpMode_Auto") != 1:
            caput("Tgt-HeC1010:Proc-V-001b:Cmd_Auto", 1)
            wait("Tgt-HeC1010:Proc-V-001b:OpMode_Auto", 1)
        if caget("Tgt-HeC1010:Proc-YSV-005a:OpMode_Auto") != 1:
            caput("Tgt-HeC1010:Proc-YSV-005a:Cmd_Auto", 1)
            wait("Tgt-HeC1010:Proc-YSV-005a:OpMode_Auto", 1)
        if caget("Tgt-HeC1010:Proc-YSV-005b:OpMode_Auto") != 1:
            caput("Tgt-HeC1010:Proc-YSV-005b:Cmd_Auto", 1)
            wait("Tgt-HeC1010:Proc-YSV-005b:OpMode_Auto", 1)
    elif caget("Tgt-HeC1010:Ctrl-PLC-001:FB_State") > 100:
        DEBUG("Go to stopping")
        caput("Tgt-HeC1010:Ctrl-PLC-001:P_State", 400)
        wait("Tgt-HeC1010:Ctrl-PLC-001:FB_State", 100)

    if caget("Tgt-HeC1010:Ctrl-PLC-001:FB_State") != 100:
        DEBUG("Go to standby")
        caput("Tgt-HeC1010:Ctrl-PLC-001:P_State", 100)
        wait("Tgt-HeC1010:Ctrl-PLC-001:FB_State", 100)

    DEBUG("init done")
