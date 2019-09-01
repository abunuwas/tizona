import os

import click


class State:

    def __init__(self):
        self.aws_profile = ''
        self.aws_region = ''
        self.verbosity = 0
        self.tizona_config = ''


pass_state = click.make_pass_decorator(State, ensure=True)


def verbosity_option(f):
    def callback(ctx, param, value):
        state = ctx.ensure_object(State)
        state.verbosity = value
        return value
    return click.option('-v', '--verbose', count=True,
                        expose_value=False,
                        help='Enables verbosity.',
                        callback=callback)(f)


def aws_profile_option(f):
    def callback(ctx, param, value):
        state = ctx.ensure_object(State)
        state.aws_profile = value
        return value
    return click.option(
        '-p', '--aws-profile',
        callback=callback,
        default=lambda: os.environ.get('AWS_DEFAULT_PROFILE', ''),
        expose_value=False,
        help='Name of the AWS profile to be used with this command',
        required=True
    )(f)


def aws_region_option(f):
    def callback(ctx, param, value):
        state = ctx.ensure_object(State)
        state.aws_region = value
        return value
    return click.option(
        '-r', '--aws-region',
        callback=callback,
        default=lambda: os.environ.get('AWS_DEFAULT_REGION', ''),
        expose_value=False,
        help='AWS region to be used with this command',
        required=True
    )(f)


def common_options(f):
    f = verbosity_option(f)
    f = aws_profile_option(f)
    f = aws_region_option(f)
    return f
