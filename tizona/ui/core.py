import operator
from functools import lru_cache, reduce

from click import ClickException

from tizona.core import AWSCommand


class UICore(AWSCommand):
    def __init__(self, project, *args, **kwargs):
        if not project:
            raise ClickException(
                'missing argument: \"project\"',
            )
        self.project = project
        super(UICore, self).__init__(*args, **kwargs)
        self.aws_lambda = self.aws_session.client('lambda')
        self.cloudformation = self.aws_session.client('cloudformation')
        self.s3 = self.aws_session.client('s3')
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
        return [
            stack for stack in stacks if self.project in stack['StackName']
        ]

    @lru_cache(maxsize=30)
    def get_stack(self, service):
        for stack in self.stacks:
            if service in stack['StackName']:
                return stack
