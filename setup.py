from setuptools import setup, find_packages

setup(
    name="pete",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    description="A python test environment for plc/epics",
    url="https://gitlab.esss.lu.se/icshwi/plc-epics-testenv",
    author="Johannes Kazantzidis",
    author_email="johannes.kazantzidis@esss.se",
    license="MIT",
    entry_points={"console_scripts": ["pete-gui=pete.gui.pete_gui:run"]},
    packages=find_packages(),
    install_requires=[
        "opcua",
        "pyepics",
        "cryptography",
        "pyqt5",
        "PyQt5-sip",
        "pytest-metadata",
        "pytest",
        "pytest-parallel",
        "cffi",
        "pytest-html",
        "pdoc3",
        "gitpython",
    ],
    zip_safe=False,
)
