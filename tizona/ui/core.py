import operator
from functools import lru_cache, reduce

import click
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
        self.cloudformation = self.aws_session.client('cloudformation')
        self.aws_lambda = self.aws_session.client('lambda')
        self.stacks = self.get_stacks()

    def get_api_url(self, api_id, stage='Prod'):
        return f'https://{api_id}.execute-api.{self.aws_region }.amazonaws.com/{stage}'  # noqa: E501

    def list_api_functions(self, api):
        api_functions = {}
        stacks = self.get_stacks()
        if api is not None:
            stacks = [stack for stack in stacks if api in stack['StackName']]
        for stack in stacks:
            resources = self.list_stack_resources(stack['StackName'])
            functions = [resource['LogicalResourceId'] for resource in resources
                         if resource['ResourceType'] == 'AWS::Lambda::Function']
            for resource in resources:
                if resource['ResourceType'] == 'AWS::ApiGateway::RestApi':
                    api_functions[resource['LogicalResourceId']] = functions
        return api_functions

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
