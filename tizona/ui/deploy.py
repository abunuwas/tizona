import operator
from functools import lru_cache, reduce
from pathlib import Path

import click
import click_spinner
import delegator
from click import ClickException
from git import Repo

from tizona.core import AWSCommand


class UICore(AWSCommand):
    def __init__(self, project, *args, **kwargs):
        if not project:
            raise ClickException(
                'missing argument: \"project\"',
            )
        self.project = project
        super(UICore, self).__init__(*args, **kwargs)
        self.cloudformation = self.aws_session.client('cloudformation')
        self.aws_lambda = self.aws_session.client('lambda')
        self.stacks = self.get_stacks()
        self.stack = self.get_stack('s3-website')
        self.stack_name = self.stack['StackName']
        self.bucket = self._get_bucket()
        self.distribution_url = f'https://s3-{self.aws_region}.amazonaws.com/{self.bucket}'  # noqa: E501

    def _get_bucket(self):
        resources = self.list_stack_resources(self.stack_name)
        for resource in resources:
            if resource['ResourceType'] == 'AWS::S3::Bucket':
                return resource['PhysicalResourceId']

    def list_stack_resources(self, stack_name):
        resources = []
        for page in self.cloudformation.get_paginator(
                'list_stack_resources'
        ).paginate(StackName=stack_name):
            for resource in page['StackResourceSummaries']:
                resources.append(resource)
        return resources

    @lru_cache(maxsize=30)
    def get_stacks(self):
        stacks = reduce(
            operator.concat,
            [page['StackSummaries'] for page in
             self.cloudformation.get_paginator('list_stacks').paginate()]
        )
        return [stack for stack in stacks if self.project in stack['StackName']]

    @lru_cache(maxsize=30)
    def get_stack(self, service):
        for stack in self.stacks:
            if service in stack['StackName']:
                return stack


class Build(UICore):
    def __init__(self, project, *args, **kwargs):
        self.project = project
        self.repo = Repo()
        self.current_hexsha = self.repo.head.object.hexsha
        self.untracked_files = self.repo.untracked_files
        super(Build, self).__init__(project, *args, **kwargs)

    def run(self):
        with click_spinner.spinner():
            delegator.run('yarn')
            delegator.run('yarn run build')
            self.update_index_file()

    def update_index_file(self):
        """
        sed -i "s/\=\//\=https\:\/\/s3-eu-west-1.amazonaws.com\/indago-maps-website\//g" dist/index.html
        """
        full_s3_url_prefix = f'{self.distribution_url}/{self.current_hexsha}/'
        with click_spinner.spinner():
            index_file = Path('dist') / 'index.html'
            contents = index_file.read_text()
            new_contents = contents.replace('=/', f'={full_s3_url_prefix}')
            index_file.write_text(new_contents)


class Deploy(UICore):
    def __init__(self, project, *args, **kwargs):
        self.project = project
        self.repo = Repo()
        self.current_hexsha = self.repo.head.object.hexsha
        self.untracked_files = self.repo.untracked_files
        super(Deploy, self).__init__(project, *args, **kwargs)

    def run(self):
        with click_spinner.spinner():
            self.upload_to_s3()
            self.tag_object()
            self.update_cloudfront()

    def upload_to_s3(self):
        s3 = self.aws_session.client('s3')
        click.secho('Uploading to s3...', fg='green')
        with click_spinner.spinner():
            s3.sync(
                Path('dist').as_posix(),
                self.bucket, self.current_hexsha
            )

    def tag_object(self):
        pass

    def update_cloudfront(self):
        pass


class Rollback(UICore):
    pass
