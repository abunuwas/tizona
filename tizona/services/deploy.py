import boto3
import click
from tabulate import tabulate

from tizona.services.general import Service


class Deploy(Service):
    def __init__(self, service, project, lambda_function, *args, **kwargs):
        self.service = service
        self.project = project
        self.lambda_function = lambda_function
        super(Deploy, self).__init__(project, *args, **kwargs)
        self.cloudformation = self.aws_session.client('cloudformation')
        self.aws_lambda = self.aws_session.client('lambda')

    def run(self):
        lambdas = self.get_functions_to_update()
        table = []
        for l in lambdas:
            config = self.aws_lambda.get_function_configuration(
                FunctionName=l['LogicalResourceId'])
            table.append(
                [config['FunctionName'], config['Handler'], config['CodeSha256'],
                 config['LastModified']])
        print(tabulate(table, headers=['Function name', 'handler', 'code sha', 'last modified']))
        click.echo(f'Deploying {self.service} for project {self.project}')

    def get_functions_to_update(self):
        stack = self.get_stack(self.service)
        resources = self.list_stack_resources(stack['StackName'])
        lambdas = [resource for resource in resources
                   if resource['ResourceType'] == 'AWS::Lambda::Function']
        if self.lambda_function:
            return [lambda_ for lambda_ in lambdas
                    if lambda_['LogicalResourceId'] == self.lambda_function]
        return lambdas
