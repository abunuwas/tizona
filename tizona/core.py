from pathlib import Path

import boto3
import click
import yaml
from click import ClickException


class TizonaCommand:
    def __init__(self, *args, **kwargs):
        self.tizona_config = self._load_tizona_config()
        self.project = self._resolve_project(kwargs.get('project'))

    @staticmethod
    def _load_tizona_config():
        tizona_config_file = Path('.tizona.yaml')
        if not tizona_config_file.exists():
            raise click.ClickException('.tizona.yaml file missing')
        return yaml.safe_load(tizona_config_file.read_text())

    def _resolve_project(self, project):
        if not project:
            project = self.tizona_config['project']
        return project

    def run(self, *args, **kwargs):
        raise NotImplementedError


class AWSCommand(TizonaCommand):
    def __init__(self, *args, **kwargs):
        super(AWSCommand, self).__init__(*args, **kwargs)
        self.aws_profile = self._resolve_aws_profile(kwargs['state'].aws_profile)  # noqa: E501
        self.aws_region = self._resolve_aws_region(kwargs['state'].aws_region)
        self.aws_session = boto3.session.Session(
            profile_name=self.aws_profile, region_name=self.aws_region
        )

    def _resolve_aws_profile(self, profile):
        if not profile:
            try:
                return self.tizona_config['aws_profile']
            except IndexError:
                raise ClickException('Please provide aws profile')
        return profile

    def _resolve_aws_region(self, region):
        if not region:
            try:
                return self.tizona_config['aws_region']
            except IndexError:
                raise ClickException('Please provide aws region')
        return region

    def run(self):
        raise NotImplementedError
