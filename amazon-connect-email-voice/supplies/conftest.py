"""Shared test fixtures: synthesize both stacks once and hand out their templates.

Tests assert against the CloudFormation template CDK would deploy, so they run
in seconds and need no AWS account. A test that passes here proves the stack
*declares* the right thing; whether Connect then *behaves* is what the live
checks in checks/live.py are for.
"""
import os
import sys

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contact_centre.core_stack import CoreStack  # noqa: E402
from contact_centre.routing_stack import RoutingStack  # noqa: E402

_ENV = cdk.Environment(account="111111111111", region="eu-central-1")


@pytest.fixture(scope="session")
def stacks():
    app = cdk.App()
    core = CoreStack(app, "ConnectCore", env=_ENV)
    routing = RoutingStack(app, "ConnectRouting", core=core, env=_ENV)
    return core, routing


@pytest.fixture(scope="session")
def core_template(stacks):
    return Template.from_stack(stacks[0])


@pytest.fixture(scope="session")
def routing_template(stacks):
    return Template.from_stack(stacks[1])
