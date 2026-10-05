#!/usr/bin/env python3
"""Read your deployed contact centre back from AWS, and the contacts it routed.

    python3 checks/live.py instance
    python3 checks/live.py email  [--since-minutes N]
    python3 checks/live.py lambda [--since-minutes N]
    python3 checks/live.py call   [--since-minutes N]

WHAT THIS CHECKS
    instance  ConnectCore is deployed; its instance is ACTIVE and CONNECT_MANAGED;
              it has a user; a user is in the agent status "Available" right now.
    email     the EmailAddress output is an address of the instance; an inbound
              flow is associated with it; the most recent inbound email contact
              reached a queue and was connected to an agent.
    lambda    the lookup function is associated with the instance and its resource
              policy lets connect.amazonaws.com call it from this instance only; the
              most recent contact, on any channel, carries a customer_id.
    call      the number is claimed for the instance and associated with the voice
              flow; the most recent inbound call reached a queue and an agent.

WHAT EVIDENCE IT READS
    Only what AWS reports, with the credentials and region of your default AWS
    configuration: the CloudFormation outputs of ConnectCore and ConnectRouting,
    then the Connect, Lambda and contact-search APIs. It never creates, changes or
    deletes anything. Each line prints the ids, names and attribute values it read,
    so a FAIL tells you what is there as well as what is missing.

    "Most recent contact" means the newest inbound contact (initiated by a customer
    or by the StartEmailContact API) in the last --since-minutes, 1440 by default.
    Contact search can lag a contact by a minute or two: if the contact you just
    made is missing, wait and run the check again.

WHAT A FAILURE HERE MEANS
    A synthesized stack that was never deployed fails, and so does a deployed one
    that routes to the wrong place. A missing stack output names the lesson that
    adds it. Exit status: 0 if every line is ok, 1 if any line is FAIL, 2 for a
    usage error.
"""
import argparse
import datetime
import json
import sys

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, NoRegionError
except ImportError:
    print("FAIL    boto3: not importable -- install requirements-dev.txt into your .venv")
    sys.exit(1)

CORE = "ConnectCore"
ROUTING = "ConnectRouting"

# Which lesson adds which stack output -- the contract every lesson follows.
ADDED_IN = {
    "InstanceId": "00-instance-and-first-agent",
    "InstanceArn": "00-instance-and-first-agent",
    "InstanceAlias": "00-instance-and-first-agent",
    "EmailAddress": "01-first-email-contact",
    "EmailAddressId": "01-first-email-contact",
    "InboundEmailFlowId": "01-first-email-contact",
    "CourseQueueId": "02-hours-queues-routing-profiles",
    "PriorityQueueId": "03-flow-logic-for-email",
    "LookupFunctionName": "04-lambda-enrichment",
    "CustomersTableName": "04-lambda-enrichment",
    "PhoneNumber": "06-a-phone-line",
    "PhoneNumberId": "06-a-phone-line",
    "InboundVoiceFlowId": "06-a-phone-line",
}

# A stack in one of these states holds no deployed version of your code.
BAD_COMPLETE = {"ROLLBACK_COMPLETE", "IMPORT_ROLLBACK_COMPLETE", "DELETE_COMPLETE"}


class Stop(Exception):
    """A failure the remaining checks of this subcommand cannot get past."""


class Report:
    def __init__(self):
        self.failed = False

    def line(self, status, name, detail):
        print(f"{status:<7} {name}: {detail}")

    def ok(self, name, detail):
        self.line("ok", name, detail)

    def fail(self, name, detail):
        self.failed = True
        self.line("FAIL", name, detail)

    def note(self, name, detail):
        self.line("note", name, detail)


def tail(identifier):
    """The bare id from an ARN (".../contact-flow/<id>"), or the value itself."""
    return identifier.rsplit("/", 1)[-1] if identifier else identifier


def same_id(a, b):
    return bool(a) and bool(b) and tail(a) == tail(b)


def aws_error(exc):
    if isinstance(exc, ClientError):
        err = exc.response.get("Error", {})
        return f"{err.get('Code', 'error')}: {err.get('Message', str(exc))}"
    return str(exc)


# ---------------------------------------------------------------------------
# stacks and their outputs
# ---------------------------------------------------------------------------

class Stacks:
    def __init__(self, session, report):
        self.cfn = session.client("cloudformation")
        self.report = report
        self.outputs = {}

    def require(self, name):
        """Describe the stack, check it is deployed, and remember its outputs."""
        try:
            stack = self.cfn.describe_stacks(StackName=name)["Stacks"][0]
        except ClientError as exc:
            if "does not exist" in aws_error(exc):
                self.report.fail(f"stack {name}", f"not deployed in this account and region -- "
                                 f"run `cdk deploy {name}` (lesson 00-instance-and-first-agent)")
                raise Stop()
            raise
        status = stack["StackStatus"]
        if status == "UPDATE_ROLLBACK_COMPLETE":
            self.report.fail(f"stack {name}", f"{status}: your last deploy failed and was rolled "
                             "back, so what is deployed is not your current code -- read the "
                             "stack events, fix, and deploy again")
            raise Stop()
        if not status.endswith("_COMPLETE") or status in BAD_COMPLETE:
            self.report.fail(f"stack {name}", f"{status}: not a deployed, settled stack")
            raise Stop()
        self.outputs[name] = {o["OutputKey"]: o["OutputValue"] for o in stack.get("Outputs", [])}
        self.report.ok(f"stack {name}", status)

    def output(self, stack, key):
        """The output's value, or a FAIL naming the lesson that adds it."""
        if stack not in self.outputs:
            self.require(stack)
        value = self.outputs[stack].get(key)
        if value:
            return value
        present = ", ".join(sorted(self.outputs[stack])) or "none"
        self.report.fail(f"output {stack}.{key}", f"missing -- lesson {ADDED_IN.get(key, '?')} "
                         f"adds it as CfnOutput id {key!r} (outputs present: {present})")
        raise Stop()


# ---------------------------------------------------------------------------
# contacts
# ---------------------------------------------------------------------------

def latest_contact(connect, instance_id, since_minutes, channels=None):
    """Newest inbound contact in the window, as SearchContacts summarises it."""
    end = datetime.datetime.now(datetime.timezone.utc)
    start = end - datetime.timedelta(minutes=since_minutes)
    criteria = {"InitiationMethods": ["INBOUND", "API"]}
    if channels:
        criteria["Channels"] = channels
    found = connect.search_contacts(
        InstanceId=instance_id,
        TimeRange={"Type": "INITIATION_TIMESTAMP", "StartTime": start, "EndTime": end},
        SearchCriteria=criteria,
        Sort={"FieldName": "INITIATION_TIMESTAMP", "Order": "DESCENDING"},
        MaxResults=1,
    )
    contacts = found.get("Contacts", [])
    return contacts[0] if contacts else None


def queue_name(connect, instance_id, queue_id):
    try:
        return connect.describe_queue(InstanceId=instance_id, QueueId=queue_id)["Queue"]["Name"]
    except ClientError:
        return "(name unreadable)"


def user_name(connect, instance_id, user_id):
    try:
        return connect.describe_user(InstanceId=instance_id, UserId=user_id)["User"]["Username"]
    except ClientError:
        return "(username unreadable)"


def attributes_of(connect, instance_id, contact):
    initial = contact.get("InitialContactId") or contact["Id"]
    return connect.get_contact_attributes(
        InstanceId=instance_id, InitialContactId=initial).get("Attributes", {})


def when(stamp):
    return stamp.strftime("%Y-%m-%d %H:%M:%S %Z") if hasattr(stamp, "strftime") else str(stamp)


def show_attributes(attrs):
    if not attrs:
        return "(none)"
    return ", ".join(f"{k}={v!r}" for k, v in sorted(attrs.items()))


def check_routed(report, connect, instance_id, contact, label):
    """The contact reached a queue and an agent took it. Prints the evidence."""
    cid = contact["Id"]
    report.ok(f"latest {label}", f"contact {cid}, {contact.get('Channel')} "
              f"{contact.get('InitiationMethod')}, started {when(contact.get('InitiationTimestamp'))}")

    queue_id = (contact.get("QueueInfo") or {}).get("Id")
    if queue_id:
        report.ok("queued", f"queue {queue_name(connect, instance_id, queue_id)!r} ({queue_id})")
    else:
        report.fail("queued", f"contact {cid} never reached a queue -- the flow ended or "
                    "disconnected before a Transfer to queue block")

    agent = contact.get("AgentInfo") or {}
    if agent.get("ConnectedToAgentTimestamp"):
        report.ok("agent", f"connected to {user_name(connect, instance_id, agent['Id'])!r} at "
                  f"{when(agent['ConnectedToAgentTimestamp'])}")
    elif agent.get("Id"):
        report.fail("agent", f"offered to {user_name(connect, instance_id, agent['Id'])!r} but "
                    "never connected -- accept it in the agent workspace, then run this again")
    elif queue_id:
        report.fail("agent", "still waiting in the queue, or abandoned there: no agent was "
                    "connected -- is your agent Available, and does the routing profile carry "
                    "this queue on this channel?")
    else:
        report.fail("agent", "no agent was connected")

    attrs = attributes_of(connect, instance_id, contact)
    report.note("attributes", show_attributes(attrs))
    if "route_reason" in attrs:
        report.note("route_reason", repr(attrs["route_reason"]))
    return attrs


def require_contact(report, contact, label, since):
    if contact is None:
        report.fail(f"latest {label}", f"no inbound {label} in the last {since} minutes -- make "
                    "one, wait a minute for contact search to index it, and run this again")
        raise Stop()
    return contact


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------

def check_instance(session, report, args):
    stacks = Stacks(session, report)
    stacks.require(CORE)
    instance_id = stacks.output(CORE, "InstanceId")
    connect = session.client("connect")

    inst = connect.describe_instance(InstanceId=instance_id)["Instance"]
    detail = f"{inst['Id']} alias {inst.get('InstanceAlias')!r} status {inst['InstanceStatus']}"
    if inst["InstanceStatus"] == "ACTIVE":
        report.ok("instance", detail)
    else:
        report.fail("instance", detail + " -- wait for ACTIVE")
    mode = inst["IdentityManagementType"]
    if mode == "CONNECT_MANAGED":
        report.ok("identity", mode)
    else:
        report.fail("identity", f"{mode}, the course needs CONNECT_MANAGED -- this cannot be "
                    "changed in place; see DESIGN.md, Instance choices")

    users = []
    for page in connect.get_paginator("list_users").paginate(InstanceId=instance_id):
        users.extend(page["UserSummaryList"])
    if not users:
        report.fail("users", "the instance has no users")
        raise Stop()
    report.ok("users", ", ".join(u["Username"] for u in users[:10]))

    # GetCurrentUserData takes exactly one of its filters; Agents takes up to 100 ids.
    by_id = {u["Id"]: u["Username"] for u in users}
    statuses = []
    ids = list(by_id)
    for i in range(0, len(ids), 100):
        kwargs = {"InstanceId": instance_id, "Filters": {"Agents": ids[i:i + 100]}}
        while True:
            page = connect.get_current_user_data(**kwargs)
            for data in page.get("UserDataList", []):
                name = (data.get("Status") or {}).get("StatusName", "(no status)")
                statuses.append((by_id.get(data["User"]["Id"], data["User"]["Id"]), name))
            if not page.get("NextToken"):
                break
            kwargs["NextToken"] = page["NextToken"]
    seen = ", ".join(f"{u}={s}" for u, s in statuses) or "no user is logged in"
    if any(s == "Available" for _, s in statuses):
        report.ok("available agent", seen)
    else:
        report.fail("available agent", f"{seen} -- log in to the agent workspace and set the "
                    "status to Available")


def check_email(session, report, args):
    stacks = Stacks(session, report)
    stacks.require(CORE)
    stacks.require(ROUTING)
    instance_id = stacks.output(CORE, "InstanceId")
    address = stacks.output(CORE, "EmailAddress")
    address_id = stacks.output(CORE, "EmailAddressId")
    connect = session.client("connect")

    described = connect.describe_email_address(InstanceId=instance_id, EmailAddressId=tail(address_id))
    if described.get("EmailAddress", "").lower() == address.lower():
        report.ok("email address", f"{described['EmailAddress']} ({described['EmailAddressId']})")
    else:
        report.fail("email address", f"output says {address!r}, the instance's address "
                    f"{tail(address_id)} is {described.get('EmailAddress')!r}")
    known = {described.get("EmailAddressId"), described.get("EmailAddressArn"), address.lower()}

    flow = None
    for page in connect.get_paginator("list_flow_associations").paginate(
            InstanceId=instance_id, ResourceType="INBOUND_EMAIL"):
        for assoc in page["FlowAssociationSummaryList"]:
            rid = assoc.get("ResourceId") or ""
            if rid in known or rid.lower() in known or tail(rid) in {tail(k) for k in known if k}:
                flow = assoc["FlowId"]
    if flow is None:
        report.fail("inbound flow", f"no INBOUND_EMAIL flow is associated with {address} -- an "
                    "address with no flow cannot start a contact (lesson 01-first-email-contact)")
    else:
        expected = stacks.outputs[ROUTING].get("InboundEmailFlowId")
        if expected is None or same_id(flow, expected):
            report.ok("inbound flow", f"{tail(flow)}" + (" = InboundEmailFlowId" if expected else ""))
        else:
            report.fail("inbound flow", f"{tail(flow)} is associated, but InboundEmailFlowId is "
                        f"{tail(expected)} -- the association points at a different flow")

    contact = require_contact(report, latest_contact(connect, instance_id, args.since_minutes,
                                                     ["EMAIL"]), "email contact", args.since_minutes)
    check_routed(report, connect, instance_id, contact, "email contact")


def check_lambda(session, report, args):
    stacks = Stacks(session, report)
    stacks.require(CORE)
    stacks.require(ROUTING)
    instance_id = stacks.output(CORE, "InstanceId")
    instance_arn = stacks.output(CORE, "InstanceArn")
    name = stacks.output(ROUTING, "LookupFunctionName")
    connect = session.client("connect")
    lam = session.client("lambda")

    fn_arn = lam.get_function(FunctionName=name)["Configuration"]["FunctionArn"]
    report.ok("function", fn_arn)

    associated = []
    for page in connect.get_paginator("list_lambda_functions").paginate(InstanceId=instance_id):
        associated.extend(page["LambdaFunctions"])
    # An association may name a qualified ARN (":alias"); compare up to the function name.
    base = fn_arn.split(":function:")[-1].split(":")[0]
    if any(a.split(":function:")[-1].split(":")[0] == base for a in associated):
        report.ok("associated", f"{name} is associated with instance {instance_id}")
    else:
        report.fail("associated", f"{name} is not in the instance's Lambda list "
                    f"({len(associated)} associated) -- add the LAMBDA_FUNCTION "
                    "IntegrationAssociation; without it the flow block fails at run time")

    try:
        policy = json.loads(lam.get_policy(FunctionName=name)["Policy"])
    except ClientError as exc:
        if "ResourceNotFound" in aws_error(exc):
            policy = {"Statement": []}
        else:
            raise
    grants = []
    for stmt in policy.get("Statement", []):
        principal = stmt.get("Principal") or {}
        service = principal.get("Service") if isinstance(principal, dict) else principal
        services = service if isinstance(service, list) else [service]
        if stmt.get("Effect") != "Allow" or "connect.amazonaws.com" not in services:
            continue
        arns = []
        for op, cond in (stmt.get("Condition") or {}).items():
            if op.startswith("Arn") or op.startswith("String"):
                for key, val in cond.items():
                    if key.lower() == "aws:sourcearn":
                        arns.extend(val if isinstance(val, list) else [val])
        grants.append(arns)
    if not grants:
        report.fail("permission", "the function's resource policy has no Allow for "
                    "connect.amazonaws.com -- CloudFormation does not add it for you")
    elif any(instance_arn in arns for arns in grants):
        report.ok("permission", f"connect.amazonaws.com allowed, source ARN {instance_arn}")
    else:
        shown = "; ".join(", ".join(a) or "no source ARN" for a in grants)
        report.fail("permission", f"connect.amazonaws.com is allowed, but scoped to {shown} -- "
                    f"scope it to the instance ARN {instance_arn}")

    contact = require_contact(report, latest_contact(connect, instance_id, args.since_minutes),
                              "contact", args.since_minutes)
    report.ok("latest contact", f"contact {contact['Id']}, {contact.get('Channel')} "
              f"{contact.get('InitiationMethod')}")
    try:
        endpoint = (connect.describe_contact(InstanceId=instance_id, ContactId=contact["Id"])
                    ["Contact"].get("CustomerEndpoint") or {}).get("Address", "(not recorded)")
        report.note("customer endpoint", endpoint)
    except ClientError:
        pass
    attrs = attributes_of(connect, instance_id, contact)
    report.note("attributes", show_attributes(attrs))
    if attrs.get("customer_id"):
        report.ok("customer_id", f"{attrs['customer_id']!r}, tier {attrs.get('tier')!r}, "
                  f"display_name {attrs.get('display_name')!r}")
    else:
        report.fail("customer_id", "the latest contact carries no customer_id user-defined "
                    "attribute -- either it came from an endpoint the table does not hold (add "
                    "yours with tools/load_customers.py), or the flow does not copy the Lambda's "
                    "result into contact attributes: a Lambda's return values are only "
                    "$.External.<key> until a Set contact attributes block after the Lambda "
                    "block copies them")


def check_call(session, report, args):
    stacks = Stacks(session, report)
    stacks.require(CORE)
    stacks.require(ROUTING)
    instance_id = stacks.output(CORE, "InstanceId")
    instance_arn = stacks.output(CORE, "InstanceArn")
    number = stacks.output(CORE, "PhoneNumber")
    number_id = stacks.output(CORE, "PhoneNumberId")
    connect = session.client("connect")

    claimed = connect.describe_phone_number(PhoneNumberId=tail(number_id))["ClaimedPhoneNumberSummary"]
    status = (claimed.get("PhoneNumberStatus") or {}).get("Status")
    detail = (f"{claimed.get('PhoneNumber')} {claimed.get('PhoneNumberCountryCode')} "
              f"{claimed.get('PhoneNumberType')} status {status}")
    if status == "CLAIMED" and claimed.get("PhoneNumber") == number:
        report.ok("number", detail)
    else:
        report.fail("number", detail + f" (output PhoneNumber is {number})")
    if claimed.get("TargetArn") == instance_arn:
        report.ok("target", f"claimed for instance {instance_id}")
    else:
        report.fail("target", f"target is {claimed.get('TargetArn')}, not {instance_arn}")

    # ListFlowAssociations accepts VOICE_PHONE_NUMBER. The docs do not say whether an
    # AssociatePhoneNumberContactFlow link is listed there, so absence is only a note.
    expected = stacks.outputs[ROUTING].get("InboundVoiceFlowId")
    ids = {claimed.get("PhoneNumberId"), claimed.get("PhoneNumberArn")}
    flow = None
    for page in connect.get_paginator("list_flow_associations").paginate(
            InstanceId=instance_id, ResourceType="VOICE_PHONE_NUMBER"):
        for assoc in page["FlowAssociationSummaryList"]:
            if assoc.get("ResourceId") in ids or tail(assoc.get("ResourceId")) in {tail(i) for i in ids if i}:
                flow = assoc["FlowId"]
    if flow is None:
        report.note("voice flow", "ListFlowAssociations lists no VOICE_PHONE_NUMBER association "
                    "for this number; it may not report AssociatePhoneNumberContactFlow links, "
                    "so the call below is the evidence")
    elif expected is None:
        report.fail("voice flow", f"number runs flow {tail(flow)}, but ConnectRouting has no "
                    "InboundVoiceFlowId output (lesson 06-a-phone-line)")
    elif same_id(flow, expected):
        report.ok("voice flow", f"{tail(flow)} = InboundVoiceFlowId")
    else:
        report.fail("voice flow", f"number runs flow {tail(flow)}, InboundVoiceFlowId is "
                    f"{tail(expected)}")
    # The contact record names no initial flow, so the flow the call ran is not
    # readable from the contact; the queue and agent are.

    contact = require_contact(report, latest_contact(connect, instance_id, args.since_minutes,
                                                     ["VOICE"]), "call", args.since_minutes)
    try:
        system = (connect.describe_contact(InstanceId=instance_id, ContactId=contact["Id"])
                  ["Contact"].get("SystemEndpoint") or {}).get("Address")
        if system and system != number:
            report.fail("dialled number", f"the latest call was to {system}, not {number}")
        elif system:
            report.ok("dialled number", system)
    except ClientError:
        pass
    check_routed(report, connect, instance_id, contact, "call")


COMMANDS = {
    "instance": (check_instance, "the stack, the instance, its users and an Available agent"),
    "email": (check_email, "the email address, its inbound flow, and the latest email contact"),
    "lambda": (check_lambda, "the lookup Lambda's grants, and customer_id on the latest contact"),
    "call": (check_call, "the claimed number, its flow, and the latest inbound call"),
}


def main(argv):
    parser = argparse.ArgumentParser(
        prog="checks/live.py",
        description="Read-only checks of your deployed contact centre. Exit 0 when every "
                    "line is ok, 1 on any FAIL.")
    sub = parser.add_subparsers(dest="command", metavar="{instance,email,lambda,call}")
    for name, (_, text) in COMMANDS.items():
        p = sub.add_parser(name, help=text, description=text)
        if name != "instance":
            p.add_argument("--since-minutes", type=int, default=1440, metavar="N",
                           help="look for contacts in the last N minutes (default 1440)")
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2
    if getattr(args, "since_minutes", 1) < 1:
        parser.error("--since-minutes must be at least 1")

    report = Report()
    try:
        session = boto3.session.Session()
        if not session.region_name:
            raise NoRegionError()
        report.note("aws", f"region {session.region_name}")
        COMMANDS[args.command][0](session, report, args)
    except Stop:
        pass
    except NoRegionError:
        report.fail("aws region", "no region configured: set AWS_REGION or a region in your profile")
    except NoCredentialsError:
        report.fail("aws credentials", "none found: configure AWS_PROFILE or credentials")
    except (ClientError, BotoCoreError) as exc:
        report.fail("aws", aws_error(exc))
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
