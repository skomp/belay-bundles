#!/usr/bin/env python3
"""Write customer records into the lookup table the ConnectRouting stack created.

    python3 tools/load_customers.py
        load every record in data/customers.json (fictional customers only)

    python3 tools/load_customers.py --add-endpoint you@your-mail.example --name Your-Name
    python3 tools/load_customers.py --add-endpoint +4930123456 --name Your-Name --tier gold
        add one record of your own, so the Lambda recognises you (lessons 04 and 07);
        an email address is lower-cased, a phone number must be E.164 (+ and digits);
        the name takes letters, digits, - and _ only, because the Lambda returns it

    python3 tools/load_customers.py --remove-endpoint you@your-mail.example
        delete one record again -- do this for your own records at teardown

SIDE EFFECT: this tool WRITES TO ONE DYNAMODB TABLE, the one named by the
ConnectRouting stack output CustomersTableName, and to nothing else. It reads the
table name from CloudFormation with your default AWS credentials and region.

A record you add with your own address or number is your personal data, stored in
your own AWS account. It goes when you remove it or destroy ConnectRouting.
"""
import argparse
import json
import os
import re
import sys

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    sys.exit("boto3 is not importable -- install requirements-dev.txt into your .venv")

STACK = "ConnectRouting"
OUTPUT = "CustomersTableName"
DEFAULT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "data", "customers.json")
E164 = re.compile(r"^\+[1-9][0-9]{6,14}$")
SAFE = re.compile(r"^[A-Za-z0-9_-]+$")


def normalise(endpoint):
    """The table's key form: a lower-cased email address, or an E.164 number."""
    value = endpoint.strip()
    if "@" in value:
        return value.lower()
    compact = re.sub(r"[\s().-]", "", value)
    if not compact.startswith("+"):
        raise ValueError(f"{endpoint!r}: a phone number must start with + and the country "
                         "code, in E.164 form, e.g. +12025550123")
    if not E164.match(compact):
        raise ValueError(f"{endpoint!r} is not an E.164 number (+, then 7 to 15 digits)")
    return compact


def table_name(session):
    cfn = session.client("cloudformation")
    try:
        stack = cfn.describe_stacks(StackName=STACK)["Stacks"][0]
    except ClientError as exc:
        sys.exit(f"cannot read stack {STACK}: {exc} -- deploy it first (lesson 04-lambda-enrichment)")
    for out in stack.get("Outputs", []):
        if out["OutputKey"] == OUTPUT:
            return out["OutputValue"]
    sys.exit(f"stack {STACK} has no output {OUTPUT!r} -- lesson 04-lambda-enrichment adds it")


def load_file(table, path):
    with open(path, encoding="utf-8") as handle:
        records = json.load(handle)
    with table.batch_writer(overwrite_by_pkeys=["endpoint"]) as batch:
        for rec in records:
            batch.put_item(Item={
                "endpoint": normalise(rec["endpoint"]),
                "customer_id": rec["customer_id"],
                "tier": rec["tier"],
                "display_name": rec["display_name"],
            })
    print(f"wrote {len(records)} records from {path} into {table.name}")


def main(argv):
    parser = argparse.ArgumentParser(prog="tools/load_customers.py",
                                     description="Write customer records into the lookup table.")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--add-endpoint", metavar="EMAIL_OR_E164",
                        help="add one record: an email address or an E.164 phone number")
    action.add_argument("--remove-endpoint", metavar="EMAIL_OR_E164",
                        help="delete the record for this endpoint")
    parser.add_argument("--name", help="display_name for --add-endpoint")
    parser.add_argument("--tier", choices=["gold", "standard"], default="gold",
                        help="tier for --add-endpoint (default gold)")
    parser.add_argument("--customer-id", default="C-LEARNER",
                        help="customer_id for --add-endpoint (default C-LEARNER); give your "
                             "email and your phone the same one, they are one customer")
    parser.add_argument("--file", default=DEFAULT_FILE,
                        help="records to load when no other option is given (default data/customers.json)")
    args = parser.parse_args(argv)
    if args.add_endpoint and not args.name:
        parser.error("--add-endpoint needs --name")
    # The Lambda returns these values to Connect, which documents only letters,
    # digits, dash and underscore in them. The customer id must stay inside that;
    # a name may break it, because lesson 04 asks you to find out what happens.
    if args.add_endpoint and args.customer_id and not SAFE.match(args.customer_id):
        parser.error(f"--customer-id {args.customer_id!r}: use only letters, digits, - and _ "
                     "(e.g. C-LEARNER), because the Lambda returns it to Connect")
    if args.add_endpoint and args.name and not SAFE.match(args.name):
        print(f"warning: --name {args.name!r} has characters outside letters, digits, - and _; "
              "the Lambda documentation does not promise these survive the trip to Connect. "
              "Lesson 04 asks you to find out.", file=sys.stderr)

    endpoint = None
    if args.add_endpoint or args.remove_endpoint:
        try:
            endpoint = normalise(args.add_endpoint or args.remove_endpoint)
        except ValueError as exc:
            parser.error(str(exc))

    try:
        session = boto3.session.Session()
        table = session.resource("dynamodb").Table(table_name(session))
        if args.add_endpoint:
            table.put_item(Item={"endpoint": endpoint, "customer_id": args.customer_id,
                                 "tier": args.tier, "display_name": args.name})
            print(f"added {endpoint} as {args.customer_id} ({args.tier}, {args.name!r}) to {table.name}")
        elif args.remove_endpoint:
            gone = table.delete_item(Key={"endpoint": endpoint}, ReturnValues="ALL_OLD")
            if gone.get("Attributes"):
                print(f"removed {endpoint} from {table.name}")
            else:
                print(f"{endpoint} was not in {table.name}; nothing removed")
        else:
            load_file(table, args.file)
    except (ClientError, BotoCoreError) as exc:
        sys.exit(f"AWS refused: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
