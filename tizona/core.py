import boto3
from click import ClickException


class TizonaCommand:
    def __init__(self, *args, **kwargs):
        # load config
        pass

    def run(self, *args, **kwargs):
        raise NotImplementedError


class AWSCommand(TizonaCommand):
    def __init__(self, *args, **kwargs):
        self.aws_profile = kwargs['state'].aws_profile
        self.aws_region = kwargs['state'].aws_region
        if not self.aws_profile:
            raise ClickException(
                'Please provide aws profile',
            )
        if not self.aws_region:
            raise ClickException(
                'Please provide aws region',
            )
        self.aws_session = boto3.session.Session(
            profile_name=self.aws_profile, region_name=self.aws_region
        )
        super(AWSCommand, self).__init__(*args, **kwargs)

    def run(self):
        pass
