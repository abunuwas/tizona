import os
import re
import shutil
import tempfile
import zipfile
from distutils.dir_util import copy_tree
from pathlib import Path

import click
from tabulate import tabulate

from tizona.services.general import Service


class VerifyAPI(Service):
    def __init__(self, project, service, *args, **kwargs):
        self.project = project
        self.service = service
        super(VerifyAPI, self).__init__(*args, **kwargs)

    def run(self):
        pass


class Deploy(Service):
    def __init__(self, service, project, lambda_function, commit, *args, **kwargs):
        self.service = service
        self.project = project
        self.hexsha = commit
        self.lambda_function = lambda_function
        self.bucket = 'indago-map'
        super(Deploy, self).__init__(project, *args, **kwargs)
        self.cloudformation = self.aws_session.client('cloudformation')
        self.aws_lambda = self.aws_session.client('lambda')

    def run(self):
        # after successfully pinged the function, we can tag the s3 object to
        # indicate that it has been deployed, date of deployment, and who
        # deployed it
        self.update_lambda_package()

    def echo_lambdas_configuration(self):
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
        # stack = self.stacks[0]
        # import pdb; pdb.set_trace()
        resources = self.list_stack_resources(stack['StackName'])
        lambdas = [resource for resource in resources
                   if resource['ResourceType'] == 'AWS::Lambda::Function']
        if self.lambda_function:
            return [lambda_ for lambda_ in lambdas
                    if lambda_['LogicalResourceId'] == self.lambda_function]
        return lambdas

    def update_lambda_package(self):
        # For now we just update the package without cloudformation. Later on,
        # I want to do this through a call to a step function that updates the
        # lambda template by pulling config values from a database and runs
        # a stack update
        aws_lambda = self.aws_session.client('lambda')
        click.secho('Updating lambdas...', fg='green')
        api_functions = self.list_api_functions(self.service).values()
        if self.lambda_function and self.lambda_function in api_functions:
            api_functions = [self.lambda_function]
        else:
            # import pdb; pdb.set_trace()
            # convert dict_values to a list and select only the first element,
            # as this is a single key value dict
            api_functions = [function_ for function_ in api_functions][0]
        api_functions = [self.lambda_function] if self.lambda_function else api_functions  # noqa: E501
        for function_ in api_functions:
            click.secho(f'Updating function {function_}', fg='yellow')
            aws_lambda.update_function_code(
                FunctionName=function_, S3Bucket=self.bucket,
                S3Key=self.hexsha, Publish=True
            )

    def ping(self):
        pass

    def rollback(self):
        pass
