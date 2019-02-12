import click
from click_help_colors import HelpColorsGroup, HelpColorsCommand

from tizona.decorators import common_options, pass_state
from tizona.ui.deploy import Build, Deploy


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
@click.option('--project')
@common_options
@pass_state
def build(state, project):
    return Build(project=project, state=state).run()


@ui.command(
    cls=HelpColorsCommand,
    help_options_color='green'
)
@click.option('--project')
@common_options
@pass_state
def deploy(state, project):
    return Deploy(project=project, state=state).run()
