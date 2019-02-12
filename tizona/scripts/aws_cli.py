import click
from click_help_colors import HelpColorsGroup, HelpColorsCommand

from tizona.aws.cloudformation import ListStacks, ListStackResources, Diff, \
    Launch
from tizona.decorators import pass_state, common_options


@click.group(
    cls=HelpColorsGroup,
    help_headers_color='yellow',
    help_options_color='green'
)
@click.pass_context
def aws(ctx):
    pass


@aws.command(
    cls=HelpColorsCommand,
    help_options_color='green',
    name='list-stacks'
)
@click.option('--project')
@common_options
@pass_state
def list_stacks(state, project):
    return ListStacks(project=project, state=state).run()


@aws.command(
    cls=HelpColorsCommand,
    help_options_color='green',
    name='list-stack-resources'
)
@click.option('--project')
@click.option('--stack')
@common_options
@pass_state
def list_stack_resources(state, stack, project):
    return ListStackResources(project=project, stack=stack, state=state).run()


@aws.command(
    cls=HelpColorsCommand,
    help_options_color='green'
)
@click.option('--project')
@click.option('--stack')
@common_options
@pass_state
def diff(state, stack, project):
    return Diff(project=project, stack=stack, state=state).run()


@aws.command(
    cls=HelpColorsCommand,
    help_options_color='green'
)
@click.option('--project')
@click.option('--stack')
@common_options
@pass_state
def launch(state, stack, project):
    return Launch(project=project, stack=stack, state=state).run()


