from tizona.core import AWSCommand


class Cloudformation(AWSCommand):
    def __init__(self, *args, **kwargs):
        super(Cloudformation, self).__init__(*args, **kwargs)
        self.cloudformation = self.aws_session.client('cloudformation')

    def list_stacks(self):
        paginator = self.cloudformation.get_paginator('list_stacks').paginate()
        return [page['StackSummaries'] for page in paginator]
