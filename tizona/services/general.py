import operator
from functools import lru_cache, reduce

import click

from tizona.aws.apigateway import ApiGatewayMixin
from tizona.core import AWSCommand
from tizona.services.dataclasses import Api


class Service(AWSCommand):
    def __init__(self, project, *args, **kwargs):
        self.project = project
        super(Service, self).__init__(*args, **kwargs)
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


class ListFunctions(Service):
    def __init__(self, api, project, *args, **kwargs):
        self.project = project
        self.api = api
        super(ListFunctions, self).__init__(project, *args, **kwargs)

    def run(self):
        api_functions = self.list_api_functions(self.api)
        for api_function, functions in api_functions.items():
            click.secho(api_function, bold=True, fg='green')
            for function_ in functions:
                click.secho(f'  {function_}', fg='yellow')


class GetApi(Service, ApiGatewayMixin):
    def __init__(self, project, service, *args, **kwargs):
        self.project = project
        self.service = service
        super(GetApi, self).__init__(project, *args, **kwargs)

    def run(self):
        rest_api = None
        functions = []
        stack = self.get_stack(self.service)
        resources = self.list_stack_resources(stack['StackName'])
        for resource in resources:
            if resource['ResourceType'] == 'AWS::ApiGateway::RestApi':
                rest_api = resource
            elif resource['ResourceType'] == 'AWS::Lambda::Function':
                functions.append(resource)
            else:
                pass
        rest_api_id = rest_api["PhysicalResourceId"]
        api = Api(api_id=rest_api_id, apigateway_client=self.apigateway, aws_region=self.aws_region)

        click.secho(f'Authorizers: {", ".join(api.authorizers)}', fg='green')
        click.secho(f'Url: {api.url}', fg='green')
        click.secho('Paths:', fg='green')
        for resource, methods in api.resources.items():
            click.secho(f'{resource}', fg='yellow')
            for method, integration in methods.items():
                click.secho(f'  {method}: {integration}')
        # get_rest_api -> EDGE
        # get_authorizers -> list[dict(id, name, type)]
        # get-integation (RestApiId, ResourceId, HttpMethod)
        # get-resource(RestApiId, ResourceId) don't see this useful, the next
        # ---------------------------one provides the same info for everything
        # get-resources (RestApiId) -> list[dict(id, path, resourceMethods)]
        # get-method (RestApiId, ResourceId, HttpMethod) -> dict(authorizationType,
        # ------------authorizerId, apiKeyRequired, methodIntegration: dict(uri),
        # ------------timeoutInMillis, cacheNamespace)
        # get-domain-names -> list[dict(domainName)]

        # get-base-path-mappings --domain-name
        # get-base-path-mapping
        # we need a stack for base path mappings, at the moment is just the naked
        # url
        # get-domain-name
        # get-domain-names


class ListApis(Service, ApiGatewayMixin):
    def __init__(self, project, *args, **kwargs):
        super(ListApis, self).__init__(project, *args, **kwargs)

    def run(self):
        api_ids = []
        stacks = self.get_stacks()
        resources = reduce(
            operator.concat,
            [self.list_stack_resources(stack['StackName']) for stack in stacks]
        )
        for resource in resources:
            if resource['ResourceType'] == 'AWS::ApiGateway::RestApi':
                api_ids.append(resource['PhysicalResourceId'])
        for api_id in api_ids:
            api = Api(api_id=api_id, apigateway_client=self.apigateway, aws_region=self.aws_region)
            click.secho(f'Authorizers: {", ".join(api.authorizers)}',
                        fg='green')
            click.secho(f'Url: {api.url}', fg='green')
            click.secho('Paths:', fg='green')
            for resource, methods in api.resources.items():
                click.secho(f'{resource}', fg='yellow')
                for method, integration in methods.items():
                    click.secho(f'  {method}: {integration}')
            click.echo('')
