import os
import re
import shutil
import tempfile
import zipfile
from distutils.dir_util import copy_tree
from pathlib import Path

import click
import click_spinner
import delegator
from git import Repo
from tabulate import tabulate

from tizona.exceptions import BuildError
from tizona.services.general import Service


class VerifyAPI(Service):
    def __init__(self, project, service, *args, **kwargs):
        self.project = project
        self.service = service
        super(VerifyAPI, self).__init__(*args, **kwargs)

    def run(self):
        pass


class Build(Service):
    def __init__(self, project, service, lambda_function, *args, **kwargs):
        self.lambda_function = lambda_function
        self.bucket = 'indago-map'
        self.project = project
        self.service = service
        self.dist_dir = Path.cwd() / 'dist'
        self.src_dir = Path.cwd() / 'src'
        self.repo = Repo()
        self.current_hexsha = self.repo.head.object.hexsha
        self.untracked_files = self.repo.untracked_files
        super(Build, self).__init__(project, *args, **kwargs)

    def run(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            # self.check_files_committed()
            # self.make_dist_dir()
            # self.install_dependencies()
            # self.clean_dependencies()
            # self.copy_dependencies()
            # self.copy_src()
            # self.make_zip(tmpdirname)
            # self.upload_s3(tmpdirname)
            self.update_lambda_package()
            self.ping()
            # ping the service to make sure it works alright, otherwise roll it back
            # self.rollback()
        return self.current_hexsha

    def make_dist_dir(self):
        """
        Creates a directory called `dist` where the build is stored. If the
        directory already exists, it removes it first along with its contents
        to make sure we create a fresh new build.
        """
        if self.dist_dir.exists():
            click.secho('Removing `dist` directory for fresh build...', fg='green')  # noqa: E501
            shutil.rmtree(self.dist_dir.as_posix())
        self.dist_dir.mkdir()

    def check_files_committed(self):
        """
        The deployed build is named after the current commit in the app repo,
        so we cannot build the app if there are any uncommitted changes. We
        look for unstaged files and staged but uncommitted files. Untracked
        files will be ignored during the build.
        """
        # staged but uncommitted
        uncommitted = self.repo.index.diff(self.current_hexsha)
        # unstaged changes
        unstaged = self.repo.index.diff(None)
        if uncommitted or unstaged:
            raise BuildError(
                'There are uncommitted changes in the repo. Please stash or '
                'commit before starting a new build.'
            )

    @staticmethod
    def install_dependencies():
        click.secho('Installing dependencies...', fg='green')
        with click_spinner.spinner():
            delegator.run('pipenv install')

    @staticmethod
    def install_lambda_packages():
        pass

    @staticmethod
    def clean_dependencies():
        click.secho('Removing uncommitted dependencies...', fg='green')
        with click_spinner.spinner():
            delegator.run('pipenv clean')

    def copy_dependencies(self):
        site_packages_dir = self._resolve_site_packages_dir()
        click.secho('Copying dependencies...', fg='green')
        with click_spinner.spinner():
            copy_tree(site_packages_dir.as_posix(), self.dist_dir.as_posix())

    @staticmethod
    def _resolve_site_packages_dir():
        pipenv_dir = delegator.run('pipenv --venv').out.strip()
        # The following returns a string of the sort `Python 3.6.6`
        python_version = delegator.run('`pipenv --py` --version').out.strip()
        # The regex below takes `3.6` from `Python 3.6.6`
        python_dir = 'python' + re.search(r'\d\.\d', python_version).group(0)
        site_packages_dir = Path(pipenv_dir) / 'lib' / python_dir / 'site-packages'  # noqa: E501
        return site_packages_dir

    def copy_src(self):
        src_dir = Path.cwd() / 'src'
        click.secho('Copying source...', fg='green')
        with click_spinner.spinner():
            copy_tree(src_dir.as_posix(), self.dist_dir.as_posix())

    def zipdir(self, path, ziph):
        # ziph is zipfile handle
        for root, dirs, files in os.walk(path):
            for file in files:
                path_to_file = Path(root) / file
                # replace our local path up to the `dist` directory so that such
                # structure doesn't get reproduced inside the zip file
                path_for_zip = path_to_file.as_posix().replace(self.dist_dir.as_posix() + '/', '')  # noqa: E501
                path_for_zip = path_for_zip.replace(self.src_dir.as_posix() + '/', '')  # noqa: E501
                ziph.write(Path(Path(root) / file).as_posix(), path_for_zip)

    def make_zip(self, tmpdirname):
        click.secho('Building zip...', fg='green')
        with click_spinner.spinner():
            zipf = zipfile.ZipFile(Path(tmpdirname) / self.current_hexsha, 'w', zipfile.ZIP_DEFLATED)  # noqa: E501
            self.zipdir(self.dist_dir, zipf)
            zipf.close()

    def upload_s3(self, tmpdirname):
        s3 = self.aws_session.client('s3')
        click.secho('Uploading to s3...', fg='green')
        with click_spinner.spinner():
            s3.upload_file(
                Path(Path(tmpdirname) / self.current_hexsha).as_posix(),
                self.bucket, self.current_hexsha
            )
        # tag the object with the name of the user who made the deployment

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
            # convert dict_values to a list and select only the first element,
            # as this is a single key value dict
            api_functions = [function_ for function_ in api_functions][0]
        api_functions = [self.lambda_function] if self.lambda_function else api_functions  # noqa: E501
        for function_ in api_functions:
            click.secho(f'Updating function {function_}', fg='yellow')
            # response = aws_lambda.update_function_code(
            #     functionName=function_, s3Bucket=self.bucket,
            #     s3Key=self.current_hexsha, publish=True
            # )
            # if response is success, print a success message, else raise an exception
            # click.secho(str(response), fg='yellow')

    def ping(self):
        pass


class Deploy(Service):
    def __init__(self, service, project, lambda_function, commit, *args, **kwargs):
        self.service = service
        self.project = project
        self.hexsha = commit
        self.lambda_function = lambda_function
        super(Deploy, self).__init__(project, *args, **kwargs)
        self.cloudformation = self.aws_session.client('cloudformation')
        self.aws_lambda = self.aws_session.client('lambda')

    def run(self):
        # after successfully pinged the function, we can tag the s3 object to
        # indicate that it has been deployed, date of deployment, and who
        # deployed it
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
            # convert dict_values to a list and select only the first element,
            # as this is a single key value dict
            api_functions = [function_ for function_ in api_functions][0]
        api_functions = [self.lambda_function] if self.lambda_function else api_functions  # noqa: E501
        for function_ in api_functions:
            click.secho(f'Updating function {function_}', fg='yellow')
            # response = aws_lambda.update_function_code(
            #     functionName=function_, s3Bucket=self.bucket,
            #     s3Key=self.hexsha, publish=True
            # )
            # if response is success, print a success message, else raise an exception
            # click.secho(str(response), fg='yellow')

    def ping(self):
        pass

    def rollback(self):
        pass
