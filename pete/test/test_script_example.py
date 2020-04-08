import time

__author__ = "Johannes Kazantzidis"
__email__ = "johannes.kazantzidis@ess.eu"
__status__ = "Production"


def lower_case(text):
    """Returns lower case version of input string.

    This is a longer test description. You can make these type of
    descriptions to classes as well as functions.

    Args:
        text (string): A text string to convert to all lower case

    Returns:
        string: The lower cased version of the input argument

    """
    time.sleep(3)
    return text.lower()


def add(a, b):
    """Returns sum of inputs.

    Args:
        a (float or int): A number.
        b (float or int): A number.

    Returns:
        int/float: a+b
    """
    time.sleep(3)
    return a + b


def test_lower():
    """All methods with names starting with 'test_' will be called when
    running the test script"""
    assert lower_case("HeLlO WoRlD") == "hello world"


def test_add():
    """Verifies that 2 + 5 = 7"""
    assert add(2, 5) == 7


# @pytest.mark.xfail(strict=True)  # Expected failure
def test_bad_add():
    """Verifies that, asserting 2 + 5 = 100, is failing"""
    assert add(2, 5) == 100
