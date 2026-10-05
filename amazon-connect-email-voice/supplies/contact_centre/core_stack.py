"""The long-lived stack: the instance, the email address, the phone number.

Deployed rarely, never torn down mid-course. Nothing here may refer to anything
in the routing stack.
"""
from aws_cdk import Stack
from constructs import Construct


class CoreStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
