from tizona.services.general import Service


class SetConfig(Service):
    def __init__(self, service, project, lambda_function, commit, *args, **kwargs):
        self.service = service
        self.project = project
        self.hexsha = commit
        self.lambda_function = lambda_function
        super(SetConfig, self).__init__(project, *args, **kwargs)
        self.cloudformation = self.aws_session.client('cloudformation')
        self.aws_lambda = self.aws_session.client('lambda')

    def run(self):
        pass
