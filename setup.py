#!/usr/bin/env python
from setuptools import setup, find_packages
from tizona import __version__


def get_install_requirements():
    return [
        'aws_requests_auth~=0.4',
        'boto3',
        'bravado~=10.0',
        'click==6.7',
        'click-help-colors==0.4',
        'click-spinner',
        'colorama==0.3.7',
        'dataclasses',
        'datadiff',
        'delegator.py',
        'gitpython',
        'humanize',
        'isodate~=0.6',
        'jsonpointer~=2.0',
        'jsonref',
        'packaging==16.8',
        'pkginfo',
        'pprintpp',
        'PyJWT~=1.5',
        'python-dotenv',
        'python-string-utils',
        'pytz',
        'pyyaml==4.2b2',
        'requests[security]',
        'sceptre',
        'tabulate',
        'termcolor',
        'timeago',
        'troposphere~=2.2',
        's3pypi',
        'semver',
        'tqdm',
    ]


setup(
    name='tizona',
    version=__version__,
    description='DevOps tool for serverless apps',
    author='Jose Antonio Haro Peralta',
    author_email='joseharoperalta@gmail.com',
    license='BSD',
    url='https://',
    packages=find_packages(exclude=['tests']),
    package_data={
        'ez_sls': [
            '../requirements*',
        ],
    },
    install_requires=get_install_requirements(),
    entry_points='''
        [console_scripts]
        tizona=tizona.scripts.tizona:cli
    ''',
    extras_require={
        'awscli': [
            'awscli'
        ],
    },
)
