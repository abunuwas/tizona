from itertools import chain
from pathlib import Path

import click
import click_spinner
import delegator
from git import Repo

from tizona.ui.core import UICore


def _run_command(command, env={}):
    output = delegator.run(command, env=env)
    if output.err:
        click.secho('The following error was encountered: ', fg='red')
        click.secho(output.err, fg='red')
        raise click.exceptions.Exit(1)


class Build:
    @staticmethod
    def run():
        with click_spinner.spinner():
            click.secho('Installing dependencies...', fg='green')
            _run_command('yarn')
            click.secho('Building the app...', fg='green')
            _run_command('yarn run build')


class Deploy(UICore):
    def __init__(self, project, *args, **kwargs):
        self.project = project
        self.repo = Repo()
        self.current_hexsha = self.repo.head.object.hexsha
        self.untracked_files = self.repo.untracked_files
        super(Deploy, self).__init__(project, *args, **kwargs)

    def run(self):
        with click_spinner.spinner():
            click.secho('Building the app...')
            Build().run()
        with click_spinner.spinner():
            self.update_index_file()
            self.upload_to_s3()
            self.tag_object()

    def update_index_file(self):
        """
        sed -i "s/\=\//\=https\:\/\/s3-eu-west-1.amazonaws.com\/indago-maps-website\//g" dist/index.html
        """  # noqa
        full_s3_url_prefix = f'{self.distribution_url}/{self.current_hexsha}/'
        with click_spinner.spinner():
            index_file = Path('dist') / 'index.html'
            index_contents = index_file.read_text()
            # replace local path references to s3 paths
            new_contents = index_contents.replace(
                '=/', f'={full_s3_url_prefix}'
            )
            hashed_index = Path('dist') / f'{self.current_hexsha}.html'
            hashed_index.write_text(new_contents)
            self.update_js_css_files()

    def _fix_static_path(self, file):
        contents = file.read_text()
        new_contents = contents.replace(
            'url(/static', f'url(/indago-maps-website/{self.current_hexsha}/static'  # noqa: E501
        )
        file.write_text(new_contents)

    def update_js_css_files(self):
        static = Path('dist/static')
        static_files = chain(
            (static / 'js').iterdir(), (static / 'css').iterdir()
        )
        for file in static_files:
            self._fix_static_path(file)

    def upload_to_s3(self):
        click.secho('Uploading to s3...', fg='green')
        with click_spinner.spinner():
            _run_command(
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
        click.echo(response)

    @staticmethod
    def tag_object():
        click.secho('Object tagged', fg='green')


class ListDeploys(UICore):
    def __init__(self, project, *args, **kwargs):
        self.project = project
        super(ListDeploys, self).__init__(project, *args, **kwargs)
        self.s3 = self.aws_session.client('s3')

    @staticmethod
    def _format_message(data):
        template = (
            '{year}-{month:02}-{day:02}:{hour:02}:{minute:02}:{second:02} - '
            '{release}'
        )
        return template.format(
            year=data['LastModified'].year,
            month=data['LastModified'].month,
            day=data['LastModified'].day,
            hour=data['LastModified'].hour,
            minute=data['LastModified'].minute,
            second=data['LastModified'].second,
            release=data['Key']
        )

    def run(self):
        for deploy in self.list_deploys():
            click.secho(self._format_message(deploy), fg='green')

    def list_deploys(self):
        paginator = self.s3.get_paginator('list_objects')
        deploys = chain.from_iterable(
            page['Contents'] for page
            in paginator.paginate(Bucket=self.bucket, Delimiter='/')
        )
        return sorted(deploys, key=lambda d: d['LastModified'])


class Release(UICore):
    def __init__(self, project, version, *args, **kwargs):
        self.project = project
        self.version = version if version else self._get_latest_version(**kwargs)  # noqa: E501
        super(Release, self).__init__(project, *args, **kwargs)
        self.distribution_id = self._get_distribution_id()
        self.cloudfront = self.aws_session.client('cloudfront')
        self.s3 = self.aws_session.client('s3')

    def _get_latest_version(self, **kwargs):
        return ListDeploys(self.project, **kwargs).list_deploys()[-1]['Key']

    def _get_distribution_id(self):
        for resource in self.list_stack_resources(self.stack_name):
            if resource['ResourceType'] == 'AWS::CloudFront::Distribution':
                return resource['PhysicalResourceId']

    def run(self):
        click.secho(f'Releasing version {self.version}', fg='green')
        with click_spinner.spinner():
            self.update_bucket_website_hosting_config()
            self.update_cloudfront_default_root_object()
        # self.reset_cloudfront_cache()

    def update_bucket_website_hosting_config(self):
        """
        routing rules:
        <RoutingRules>
          <RoutingRule>
            <Condition>
              <KeyPrefixEquals>maps</KeyPrefixEquals>
            </Condition>
            <Redirect>
              <ReplaceKeyWith/>
            </Redirect>
          </RoutingRule>
        </RoutingRules>
        """
        click.secho('Updating s3 website hosting configuration...', fg='green')
        self.s3.put_bucket_website(
            Bucket=self.bucket,
            WebsiteConfiguration={
                'ErrorDocument': {
                    'Key': self.version
                },
                'IndexDocument': {
                    'Suffix': self.version
                },

            }
        )

    def get_distribution_config(self):
        distribution_config = self.cloudfront.get_distribution_config(
            Id=self.distribution_id
        )
        return distribution_config['ETag'], distribution_config['DistributionConfig']  # noqa: E501

    def update_cloudfront_default_root_object(self):
        click.secho('Updating cloudfront distribution', fg='green')
        etag, config = self.get_distribution_config()
        config['DefaultRootObject'] = self.version
        with click_spinner.spinner():
            self.cloudfront.update_distribution(
                DistributionConfig=config, Id=self.distribution_id, IfMatch=etag  # noqa: E501
            )
            waiter = self.cloudfront.get_waiter('distribution_deployed')
            waiter.wait(
                Id=self.distribution_id,
                WaiterConfig={'Delay': 20, 'MaxAttempts': 110}
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


class CurrentRelease(UICore):
    def __init__(self, project, *args, **kwargs):
        self.project = project
        super(CurrentRelease, self).__init__(project, *args, **kwargs)

    def run(self):
        current_version = self.s3.get_bucket_website(
            Bucket=self.bucket
        )['IndexDocument']['Suffix']
        click.secho(
            f'Currently deployed version: {current_version}', fg='green'
        )


class Rollback(UICore):
    def __init__(self, project, *args, **kwargs):
        self.project = project
        super(Rollback, self).__init__(project, *args, **kwargs)

    def run(self):
        pass


class DeleteDeploy(UICore):
    def __init__(self, project, *args, **kwargs):
        self.project = project
        super(DeleteDeploy, self).__init__(project, *args, **kwargs)

    def run(self):
        pass
