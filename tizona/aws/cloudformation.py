import difflib
import json
import operator
import uuid
from functools import lru_cache, reduce
from pathlib import Path

import click
import click_spinner
from click import ClickException
from sceptre.context import SceptreContext
from sceptre.plan.plan import SceptrePlan
from tabulate import tabulate

from tizona.core import AWSCommand


class CloudFormation(AWSCommand):
    def __init__(self, project, *args, **kwargs):
        if not project:
            raise ClickException(
                'missing argument: \"project\"',
            )
        self.project = project
        super(CloudFormation, self).__init__(*args, **kwargs)
        self.cloudformation = self.aws_session.client('cloudformation')
        self.aws_lambda = self.aws_session.client('lambda')
        self.stacks = self.get_stacks()

    def list_stacks(self):
        paginator = self.cloudformation.get_paginator('list_stacks').paginate()
        return [page['StackSummaries'] for page in paginator]

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


class ListStacks(CloudFormation):
    def __init__(self, project, *args, **kwargs):
        self.project = project
        super(ListStacks, self).__init__(project, *args, **kwargs)

    def run(self):
        for stack in self.stacks:
            click.secho(stack['StackName'], fg='green')


class ListStackResources(CloudFormation):
    def __init__(self, project, stack, *args, **kwargs):
        self.project = project
        self.stack = stack
        super(ListStackResources, self).__init__(project, *args, **kwargs)

    def run(self):
        resources = self.list_stack_resources(self.stack)
        table = []
        for resource in resources:
            table.append(
                [resource['LogicalResourceId'], resource['ResourceType']]
            )
        click.secho(
            tabulate(table, headers=['Logical Resource Id', 'ResourceType']), fg='green'  # noqa: E501
        )


class Sceptre(CloudFormation):
    def __init__(self, project, stack, *args, **kwargs):
        self.project = project
        self.stack = stack
        super(Sceptre, self).__init__(project, *args, **kwargs)
        self.stack_name = self.get_stack(stack)['StackName']
        context = SceptreContext(
            self.resolve_sceptre_project_path().as_posix(),
            self.resolve_stack_file().as_posix(),
            ignore_dependencies=True
        )
        self.plan = SceptrePlan(context)

    @staticmethod
    def resolve_sceptre_project_path():
        cwd = Path().cwd()
        for content in cwd.iterdir():
            if 'infrastructure' in content.as_posix() and content.is_dir():
                return content
        raise ClickException(
            'We could not find an infrastructure folder. Make sure you are at '
            'the top-level directory of the project you are trying to deploy.'
        )

    def resolve_stack_file(self):
        stack_file_path = self.stack
        if not self.stack.endswith('.yaml'):
            stack_file_path += '.yaml'
        if not self.stack.startswith('prod/'):
            stack_file_path = Path('prod') / stack_file_path
        return Path(stack_file_path)

    def create_change_set(self, change_set_name):
        with click_spinner.spinner():
            self.plan.create_change_set(change_set_name)
            self.plan.wait_for_cs_completion(change_set_name)


class Diff(Sceptre):
    def __init__(self, project, stack, *args, **kwargs):
        self.project = project
        self.stack = stack
        super(Diff, self).__init__(project, stack, *args, **kwargs)

    def run(self):
        change_set_name = f'a-{uuid.uuid1().hex}'
        self.create_change_set(change_set_name)
        deployed_template = self.cloudformation.get_template(
            StackName=self.stack_name
        )
        new_template = self.cloudformation.get_template(
            StackName=self.stack_name, ChangeSetName=change_set_name
        )
        # import pdb; pdb.set_trace()
        # Transform the dictionaries into json objects, ordering the keys to
        # make them comparable, indent them for better visualisation and
        # split into lines so that we can do the diff
        deployed_template = json.dumps(
            deployed_template['TemplateBody'], sort_keys=True, indent=2
        ).splitlines()
        new_template = json.dumps(
            new_template['TemplateBody'], sort_keys=True, indent=2
        ).splitlines()
        for line in difflib.unified_diff(
                deployed_template, new_template, fromfile='deployed template',
                tofile='local template', lineterm=''
        ):
            if line.startswith('-'):
                # lines that are going to be removed appear in red
                click.secho(line, fg='red')
            elif line.startswith('+'):
                # lines that are going to be added appear in green
                click.secho(line, fg='green')
            else:
                click.secho(line)


class Launch(Sceptre):
    def __init__(self, project, stack, *args, **kwargs):
        self.project = project
        self.stack = stack
        super(Launch, self).__init__(project, stack, *args, **kwargs)
        self.stack_name = self.get_stack(stack)['StackName']

    def run(self):
        # The change set name pattern has to be [a-zA-Z][-a-zA-Z0-9]*
        change_set_name = f'a-{uuid.uuid1().hex}'
        self.create_change_set(change_set_name)
        with click_spinner.spinner():
            # self.plan.execute_change_set(change_set_name)
            # self.plan.wait_for_cs_completion()
            self.plan.launch()
        click.secho('Stack updated', fg='green')
