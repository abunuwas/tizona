import click
from click_help_colors import HelpColorsGroup, HelpColorsCommand

from tizona.decorators import common_options, pass_state
from tizona.ui.deploy import Build, Deploy, ListDeploys, Release, \
    CurrentRelease


@click.group(
    cls=HelpColorsGroup,
    help_headers_color='yellow',
    help_options_color='green'
)
def ui():
    pass


@ui.command(
    cls=HelpColorsCommand,
    help_options_color='green'
)
def build():
    return Build().run()


@ui.command(
    cls=HelpColorsCommand,
    help_options_color='green'
)
@click.option('--project')
@common_options
@pass_state
def deploy(state, project):
    return Deploy(project=project, state=state).run()


@ui.command(
    cls=HelpColorsCommand,
    help_options_color='green'
)
@click.option('--project')
@common_options
@pass_state
def list_deploys(state, project):
    return ListDeploys(project=project, state=state).run()


@ui.command(
    cls=HelpColorsCommand,
    help_options_color='green'
)
@click.option('--project')
@click.option('--version')
@common_options
@pass_state
def release(state, version, project):
    return Release(project=project, version=version, state=state).run()


@ui.command(
    cls=HelpColorsCommand,
    help_options_color='green'
)
@click.option('--project')
@common_options
@pass_state
def current_release(state, project):
    return CurrentRelease(project, state=state).run()
