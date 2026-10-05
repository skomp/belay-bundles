#!/usr/bin/env python3
"""Create three test email contacts for you to follow through your contact centre.

    python3 tools/scenarios.py

SIDE EFFECT: this tool CREATES THREE INBOUND EMAIL CONTACTS on your instance, with
the Connect StartEmailContact API, addressed to the ConnectCore stack's EmailAddress
output. Each one runs the inbound flow associated with that address -- the same flow
a real email would run -- and will be offered to your agent like any other contact.
It changes nothing else. The senders are fictional addresses on example.com, so the
replies your agent sends to them go nowhere.

It prints a label (A, B, C) and the contact id for each, and nothing about where they
went. Finding that out, from the evidence, is the lesson.

Before it sends anything it reads your lookup table (ConnectRouting output
CustomersTableName) to check that data/customers.json was loaded, because the three
contacts were built against those records.
"""
import os
import sys

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    sys.exit("boto3 is not importable -- install requirements-dev.txt into your .venv")

SCENARIOS = [
    {
        "label": "A",
        "sender": "ada.fairweather@example.com",
        "display": "Ada Fairweather",
        "subject": "Copy of my March invoice",
        "body": "Hello,\n\nCould you send me a copy of the invoice for March?\n\nThanks,\nAda",
    },
    {
        "label": "B",
        "sender": "rowan.quill@example.com",
        "display": "Rowan Quill",
        "subject": "urgent: my order has not arrived",
        "body": "Hi,\n\nOrder 4471 was due on Monday and has not arrived. Please help.\n\nRowan",
    },
    {
        "label": "C",
        "sender": "sam.okonkwo@example.com",
        "display": "Sam Okonkwo",
        "subject": "Question about your opening hours",
        "body": "Hello,\n\nAre you open on public holidays?\n\nBest regards,\nSam",
    },
]


def outputs(cfn, stack):
    try:
        found = cfn.describe_stacks(StackName=stack)["Stacks"][0]
    except ClientError as exc:
        sys.exit(f"cannot read stack {stack}: {exc} -- is it deployed in this region?")
    return {o["OutputKey"]: o["OutputValue"] for o in found.get("Outputs", [])}


def need(values, stack, key, lesson):
    if not values.get(key):
        sys.exit(f"stack {stack} has no output {key!r} -- lesson {lesson} adds it")
    return values[key]


def check_table(session, routing):
    """Warn, without sending anything yet, if the table does not match the scenarios."""
    name = routing.get("CustomersTableName")
    if not name:
        print("warning: ConnectRouting has no CustomersTableName output, so the lookup "
              "table cannot be checked (lesson 04-lambda-enrichment adds it)")
        return
    table = session.resource("dynamodb").Table(name)
    known = table.get_item(Key={"endpoint": SCENARIOS[0]["sender"]}).get("Item")
    if not known:
        print(f"warning: {SCENARIOS[0]['sender']} is in data/customers.json but not in table "
              f"{name} -- run tools/load_customers.py first, or these contacts will not "
              "test what they were built to test")
    for scenario in SCENARIOS[1:]:
        if table.get_item(Key={"endpoint": scenario["sender"]}).get("Item"):
            print(f"warning: {scenario['sender']} is in table {name}, but these scenarios "
                  "expect it not to be -- remove it with tools/load_customers.py "
                  "--remove-endpoint")


def main():
    try:
        session = boto3.session.Session()
        cfn = session.client("cloudformation")
        core = outputs(cfn, "ConnectCore")
        instance_id = need(core, "ConnectCore", "InstanceId", "00-instance-and-first-agent")
        address = need(core, "ConnectCore", "EmailAddress", "01-first-email-contact")
        check_table(session, outputs(cfn, "ConnectRouting"))

        connect = session.client("connect")
        print(f"sending three emails to {address}:")
        for scenario in SCENARIOS:
            # No ContactFlowId: the address's own inbound flow must run, as for real mail.
            started = connect.start_email_contact(
                InstanceId=instance_id,
                FromEmailAddress={"EmailAddress": scenario["sender"],
                                  "DisplayName": scenario["display"]},
                DestinationEmailAddress=address,
                EmailMessage={
                    "MessageSourceType": "RAW",
                    "RawMessage": {
                        "Subject": scenario["subject"],
                        "Body": scenario["body"],
                        "ContentType": "text/plain",
                    },
                },
                Name=f"Scenario {scenario['label']}",
            )
            print(f"  {scenario['label']}  contact {started['ContactId']}  "
                  f"from {scenario['sender']}  subject {scenario['subject']!r}")
    except (ClientError, BotoCoreError) as exc:
        sys.exit(f"AWS refused: {exc}")
    print("Now find out, from the evidence, where each one went and why.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
