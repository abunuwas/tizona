import click
from click import ClickException
from click_help_colors import HelpColorsCommand, HelpColorsGroup

from tizona.decorators import common_options, pass_state
from tizona.services.deploy import Deploy, Build
from tizona.services.general import ListFunctions, GetApi, ListApis


@click.group(
    cls=HelpColorsGroup,
    help_headers_color='yellow',
    help_options_color='green'
)
@click.pass_context
def service(ctx):
    pass


@service.command(
    cls=HelpColorsCommand,
    help_options_color='green',
    name='list-functions'
)
@click.option('--api')
@click.option('--project')
@common_options
@pass_state
def list_functions(state, api, project):
    return ListFunctions(api=api, project=project, state=state).run()


@service.command(
    cls=HelpColorsCommand,
    help_options_color='green',
    name='list-apis'
)
@click.option('--project')
@common_options
@pass_state
def list_apis(state, project):
    return ListApis(project=project, state=state).run()


@service.command(
    cls=HelpColorsCommand,
    help_options_color='green',
    name='get-function-config'
)
def get_function_config():
    pass


@service.command(
    cls=HelpColorsCommand,
    help_options_color='green',
    name='get-api'
)
@click.argument('service')
@click.option('--project')
@common_options
@pass_state
def get_api(state, service, project):
    GetApi(project=project, service=service, state=state).run()


@service.command(
    cls=HelpColorsCommand,
    help_options_color='green',
    name='get-deployments'
)
@click.argument('service')
@click.option('--project')
@common_options
@pass_state
def get_deployments():
    pass


@service.command(
    cls=HelpColorsCommand,
    help_options_color='green',
)
@click.argument('service')
@click.option('--project')
@click.option('--lambda-function')
@common_options
@pass_state
def build(state, service, project, lambda_function):
    return Build(project=project, service=service,
                 lambda_function=lambda_function, state=state).run()


@service.command(
    cls=HelpColorsCommand,
    help_options_color='green',
    name='set-function-config'
)
@click.argument('service')
@click.option('--project')
@common_options
@pass_state
def set_function_config():
    pass


@service.command(
    cls=HelpColorsCommand,
    help_options_color='green'
)
@click.argument('service')
@click.option('--project')
@common_options
@pass_state
def rollback():
    pass


@service.command(
    cls=HelpColorsCommand,
    help_options_color='green'
)
@click.argument('service')
@click.option('--project', help='Project to which the service belongs')
@click.option('--lambda-function', help='Lambda function to be updated')
@click.option('--local', help='Package and deploy the your local code', default=True)  # noqa: E501
@click.option('--commit', help='Commit to be deployed. A packaged version of '
                               'the code under this commit must exist in s3')
@common_options
@pass_state
def deploy(state, service, project, lambda_function, local, commit):
    if not local and not commit:
        raise ClickException('You must specify either local or commit')
    if local:
        commit = Build(project=project, service=service,
                       lambda_function=lambda_function, state=state).run()
    return Deploy(
        service=service, project=project, lambda_function=lambda_function,
        commit=commit, state=state
    ).run()