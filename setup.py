from setuptools import setup , find_packages

setup(

    name= 'girgit',
    version= '2.2',
    packages=find_packages(),

    install_requires=[
        "boto3"
    ],
    entry_points=
    {
    "console_scripts" : [
        "girgit = girgit:main",
    ],
    },
)
