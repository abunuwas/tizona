import click
from click_help_colors import HelpColorsGroup


@click.group(
    cls=HelpColorsGroup,
    help_headers_color='yellow',
    help_options_color='green'
)
def aws():
    pass
