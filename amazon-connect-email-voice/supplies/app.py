#!/usr/bin/env python3
"""CDK entry point: the two stacks of this contact centre.

ConnectCore    -- long-lived: the instance, the email address, the phone number.
ConnectRouting -- churning: hours, queues, routing profiles, flows, the Lambda.

References pass one way only, from ConnectCore to ConnectRouting. See DESIGN.md,
"Stack split", in your tutorial/ directory.

The account and region come from your AWS credentials and configuration, so the
region you chose in lesson 00 is set once, there, and nowhere in this code.
"""
import os

import aws_cdk as cdk

from contact_centre.core_stack import CoreStack
from contact_centre.routing_stack import RoutingStack

app = cdk.App()
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)

core = CoreStack(app, "ConnectCore", env=env)
RoutingStack(app, "ConnectRouting", core=core, env=env)

app.synth()
