#!/usr/bin/env python
from setuptools import setup, find_packages
from tizona import __version__


def get_install_requirements():
    return [
        'aws_requests_auth',
        'boto3',
        'bravado',
        'click',
        'click-help-colors',
        'click-spinner',
        'colorama',
        'dataclasses',
        'datadiff',
        'delegator.py',
        'gitpython',
        'humanize',
        'isodate',
        'jsonpointer',
        'jsonref',
        'packaging',
        'pkginfo',
        'pprintpp',
        'PyJWT',
        'python-dotenv',
        'python-string-utils',
        'pytz',
        'pyyaml',
        'requests[security]',
        'sceptre',
        'tabulate',
        'termcolor',
        'timeago',
        'troposphere',
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
