"""The churning stack: hours, queues, routing profiles, flows, the Lambda.

Redeployed freely. It receives what it needs from the core stack through the
`core` argument; it never reaches back the other way.
"""
from aws_cdk import Stack
from constructs import Construct

from contact_centre.core_stack import CoreStack


class RoutingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, core: CoreStack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.core = core
