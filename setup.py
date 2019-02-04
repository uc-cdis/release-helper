from setuptools import setup

setup(
    name="gen3git",
    description="Helps with release.",
    license="Apache",
    py_modules=["gen3git"],
    install_requires=['enum;python_version<"3.4"', "PyGithub", "requests", "gitpython"],
    entry_points={"console_scripts": ["gen3git=gen3git:main"]},
)
