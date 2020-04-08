import os

from epics import caget
import git
from petenv.opc_client import OPCClient

__author__ = "Johannes Kazantzidis"
__email__ = "johannes.kazantzidis@ess.eu"
__status__ = "Production"


def pytest_configure(config):
    """Configuration for reports.

    When running a test with the '--metadata petenv' flag, this code
    will be run to add metadata into the top of the generated
    report. Note that if the variables below are `None`, petenv will ask
    you for the information in the command line interface. You may
    hardcode the values to avoid this command line interaction if you prefer.
    """
    # Hard code these values to avoid being asked when running petenv with
    # metadata flag. ###########################################################
    IP = None  # PLC ip address e.g. "172.30.4.163"
    PETENV_REPO = None  # Path to petenv e.g. "~/petenv"
    PLCF_REPO = None  # Path to plcfactory e.g. "~/ics_plc_factory/"
    OPI_REPO = None  # Path to the ess-opis repo e.g. "~/ess-opis/"
    PVS = None  # Path to a list of PVs e.g. "~/thccs/THCCS_PVs.list"
    V_VER = None  # PLC project version in versiondog e.g. "6"
    V_PATH = None  # Path to plc project in versiondog e.g.
    # "\=ESS\INFR [Infrastructure]\ICS_MASTER_LIBRARY\TIA Portal"
    ############################################################################

    if "petenv" in config._metadata:
        # petenv
        verify_repo(config, "Path to petenv repo: ", " petenv", PETENV_REPO)

        # plc factory
        verify_repo(config, "Path to PLC Factory repo: ", " plc factory", PLCF_REPO)

        # opi
        verify_repo(config, "Path to OPI_REPO repository: ", " OPI_REPO", OPI_REPO)

        # plc ip
        if IP is None:
            IP = input("PLC IP: ")

        if IP:
            config._metadata[" PLC IP"] = IP
            client = OPCClient(IP)
            client.connect()
            objects = client.get_root_node().get_child("0:Objects")
            children = objects.get_children()
            cpu = children[-1]

            config._metadata[" PLC softwareRevision"] = cpu.get_child(
                "2:SoftwareRevision"
            ).get_value()

            config._metadata[" PLC SerialNumber"] = cpu.get_child(
                "2:SerialNumber"
            ).get_value()

            config._metadata[" PLC OrderNumber"] = cpu.get_child(
                "3:OrderNumber"
            ).get_value()

            config._metadata[" PLC Model"] = str(
                cpu.get_child("2:Model").get_value()
            ).split()[-2]

            config._metadata[" PLC HardwareRevision"] = cpu.get_child(
                "2:HardwareRevision"
            ).get_value()

            client.disconnect()
        else:
            config._metadata[" PLC attributes"] = "Ignored"

        # versiondog
        if V_PATH is None:
            V_PATH = input("PLC program path in VersionDog: ")

        if V_PATH:
            config._metadata[" PLC program path in VersionDog"] = V_PATH
        else:
            config._metadata[" PLC program path in VersionDog"] = "Ignored"

        if V_VER is None:
            V_VER = input("PLC program version in VersionDog: ")
        if V_VER:
            config._metadata[" PLC program version in VersionDog"] = V_VER
        else:
            config._metadata[" PLC program version in VersionDog"] = "Ignored"

        # pv list
        if PVS is None:
            PVS = os.path.expanduser(input("Path to pvlist: "))
        else:
            PVS = os.path.expanduser(PVS)

        if PVS:
            with open(PVS) as f:
                lines = f.readlines()
                for l in lines:
                    if "REQMOD" in l:
                        req = l.split(":")
                        prefix = "{}:{}".format(req[0], req[1])

                        config._metadata[" IOC asyn version"] = caget(
                            prefix + ":asyn_VER"
                        )

                        config._metadata[" IOC autosave version"] = caget(
                            prefix + ":autosave_VER"
                        )

                        config._metadata[" IOC s7 version"] = caget(
                            prefix + ":s7plc_VER"
                        )

                        config._metadata[" IOC modbus version"] = caget(
                            prefix + ":modbus_VER"
                        )

                        config._metadata[" IOC require version"] = caget(
                            prefix + ":require_VER"
                        )

                        break
        else:
            config._metadata[" EPICS/IOC attributes"] = "Ignored"


def verify_repo(config, instruction, description, repo_path):
    repo_ok = False
    while not repo_ok:
        if repo_path is None:
            repo_path = input(instruction)
        if not repo_path:
            config._metadata[instruction] = "Ignored"
            break
        else:
            try:
                set_commit(config, description, repo_path)
                repo_ok = True
            except git.exc.InvalidGitRepositoryError:
                answer = input("Invalid repository path, retry? [y/n]: ")
                if answer.lower() in ["y", "yes", "yeah"]:
                    repo_path = input(instruction)
                    continue
                elif answer.lower() in ["n", "no", "nope"]:
                    break


def set_commit(config, tag, path):
    try:
        repo = git.Repo(path)
        url = str(git.cmd.Git(path).remote(verbose=True)).split()[1]
        ref = str(repo.head.reference.log()[-1]).split()[1]
        config._metadata["{} url".format(tag)] = url
        config._metadata["{} git commit".format(tag)] = ref
    except git.exc.NoSuchPathError:
        print("'{}' is not a git repository".format(path))
