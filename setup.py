#!/usr/bin/env python
from setuptools import setup, find_packages


install_requires = [
    'boto3>=1.4.5',
    'click>=6.7',
    'configparser>=3.5.0',
    'docker>=2.4.2',
    'dockerpty>=0.4.1',
    'jsonpath>=0.75',
    'tabulate>=0.7.7',
    'humanize>=0.5.1',
    'pytz>=2017.2',
    'stringcase>=1.2.0',
    'pyyaml>=5.1.2',
    'oyaml>=0.9',
    'pygments>=2.4.2',
    'jsonpath-ng>=1.4.3'
]

classifiers = [
    'Development Status :: 4 - Alpha',
    'Environment :: Console',
    'Topic :: System :: Clustering',
]

with open('README.rst', 'r') as f:
    long_description = f.read()

setup(
    name='ecsctl',
    version='20190924',
    description='kubectl-style command line client for AWS ECS.',
    license="MIT license",
    long_description=long_description,
    author='Witold Gren',
    author_email='witold.gren@gmail.com',
    url='https://github.com/witold-gren/ecsctl',
    packages=find_packages(include=['ecsctl', 'ecsctl.commands']),
    entry_points={
        'console_scripts': [
            'ecsctl = ecsctl.__main__:main'
        ]
    },
    install_requires=install_requires,
    keywords=['ECS', 'ecsctl', 'kubectl', 'AWS', 'docker'],
    classifiers=classifiers,
    include_package_data=True,
)
