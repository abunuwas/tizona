import click
from click_help_colors import HelpColorsGroup

from tizona.scripts.aws_cli import aws
from tizona.scripts.service_cli import service
from tizona.scripts.ui_cli import ui


@click.group(
    cls=HelpColorsGroup,
    help_headers_color='yellow',
    help_options_color='green'
)
def cli():
    pass


cli.add_command(aws)
cli.add_command(service)
cli.add_command(ui)
