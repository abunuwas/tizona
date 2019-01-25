from tizona.core import AWSCommand


class ApiGatewayMixin(AWSCommand):
    def __init__(self, *args, **kwargs):
        super(ApiGatewayMixin, self).__init__(*args, **kwargs)
        self.apigateway = self.aws_session.client('apigateway')