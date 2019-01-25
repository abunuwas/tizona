import re
from dataclasses import dataclass


@dataclass
class Api:
    api_id: int
    apigateway_client: str
    aws_region: int
    stage = 'Prod'

    # The below attributes are not meant to be set by the caller
    authorizers = ''
    resources = ''
    url = ''

    def __post_init__(self):
        self.load_authorizers()
        self.load_resources()
        self.url = self.get_api_url()

    def load_authorizers(self):
        self.authorizers = [
            authorizer['name'] for authorizer in
            self.apigateway_client.get_authorizers(restApiId=self.api_id)['items']  # noqa: E501
        ]

    def get_api_url(self):
        return f'https://{self.api_id}.execute-api.{self.aws_region }.amazonaws.com/{self.stage}'  # noqa: E501

    def load_resources(self):
        self.resources = {}
        resources = [
            resource for resource in
            self.apigateway_client.get_resources(restApiId=self.api_id)['items']
            if resource.get('resourceMethods')
        ]
        for resource in resources:
            resource_path = resource['path']
            self.resources[resource_path] = {}
            for method in resource['resourceMethods']:
                self.resources[resource_path][method] = self.get_method_integration(method, resource['id'])  # noqa: E501

    def get_method_integration(self, method, resource_id):
        method_info = self.apigateway_client.get_method(
            restApiId=self.api_id, resourceId=resource_id, httpMethod=method
        )
        method_integration = method_info['methodIntegration'].get('uri')
        method_integration_regex = re.compile(r'\:(\w+)\/invocations')
        if method_integration is not None:
            return re.findall(method_integration_regex, method_integration)
        else:
            return ''
