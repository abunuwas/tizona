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
            click.secho('Installing dependencies...', fg='green')
            delegator.run('yarn')
            click.secho('Building the app...', fg='green')
            delegator.run('yarn run build')
            self.update_index_file()

    def update_index_file(self):
        """
        sed -i "s/\=\//\=https\:\/\/s3-eu-west-1.amazonaws.com\/indago-maps-website\//g" dist/index.html
        """
        full_s3_url_prefix = f'{self.distribution_url}/{self.current_hexsha}/'
        with click_spinner.spinner():
            index_file = Path('dist') / 'index.html'
            index_contents = index_file.read_text()
            new_contents = index_contents.replace('=/', f'={full_s3_url_prefix}')
            hashed_index = Path('dist') / f'{self.current_hexsha}.html'
            hashed_index.write_text(new_contents)


class Deploy(UICore):
    def __init__(self, project, *args, **kwargs):
        self.project = project
        self.repo = Repo()
        self.current_hexsha = self.repo.head.object.hexsha
        self.untracked_files = self.repo.untracked_files
        super(Deploy, self).__init__(project, *args, **kwargs)
        self.distribution_id = self._get_distribution_id()
        self.cloudfront = self.aws_session.client('cloudfront')

    def run(self):
        with click_spinner.spinner():
            self.upload_to_s3()
            self.tag_object()
            self.update_cloudfront_default_root_object()
            # self.reset_cloudfront_cache()

    def _get_distribution_id(self):
        for resource in self.list_stack_resources(self.stack_name):
            if resource['ResourceType'] == 'AWS::CloudFront::Distribution':
                return resource['PhysicalResourceId']

    def upload_to_s3(self):
        click.secho('Uploading to s3...', fg='green')
        with click_spinner.spinner():
            output = delegator.run(
                f'aws s3 sync dist/ s3://{self.bucket}/{self.current_hexsha}',
                env={
                    'AWS_DEFAULT_PROFILE': self.aws_profile,
                    'AWS_DEFAULT_REGION': self.aws_region
                }
            )
            click.secho('uploading the file...', fg='green')
            bucket = self.aws_session.resource('s3').Bucket(self.bucket)
            response = bucket.put_object(
                ACL='public-read',
                Body=Path(f'dist/{self.current_hexsha}.html').read_text(),
                ContentType='text/html',
                Key=f'{self.current_hexsha}.html',
            )
        if output.err:
            click.secho('The following error was encountered: ', fg='red')
            click.secho(output.err, fg='red')
        click.echo(response)

    def tag_object(self):
        click.secho('Object tagged', fg='green')

    def get_distribution_config(self):
        distribution_config = self.cloudfront.get_distribution_config(
            Id=self.distribution_id
        )
        return distribution_config['ETag'], distribution_config['DistributionConfig']  # noqa: E501

    def update_cloudfront_default_root_object(self):
        click.secho('Updating cloudfront distribution', fg='green')
        etag, config = self.get_distribution_config()
        config['DefaultRootObject'] = f'{self.current_hexsha}.html'
        with click_spinner.spinner():
            self.cloudfront.update_distribution(
                DistributionConfig=config, Id=self.distribution_id, IfMatch=etag
            )

    def reset_cloudfront_cache(self):
        # click.secho('Cloudfront cache reset', fg='green')
        # with click_spinner.spinner():
        #     self.cloudfront.create_invalidation(
        #         DistributionId=self.distribution_id,
        #         InvalidationBatch={
        #             'Paths': {
        #                 'Quantity': 123,
        #                 'Items': [
        #                     'string',
        #                 ]
        #             },
        #             'CallerReference': 'string'
        #         }
        #     )
        # I don't think I need to invalidate the cache because I'm changing the
        # name of the default root object
        pass


class Rollback(UICore):
    pass
