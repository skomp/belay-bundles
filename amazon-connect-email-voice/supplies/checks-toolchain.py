#!/usr/bin/env python3
"""Check that what this course assumes you already have is in place.

Reads only. Fails on what the course assumes: Python, Node.js, and the AWS CLI
with working credentials and a region. The CDK CLI and the Python packages are
installed in lesson 00, so their absence is reported as "not yet" and does not
fail this check.
"""
import shutil
import subprocess
import sys

failures = []


def report(status, name, detail):
    print(f"{status:<7} {name}: {detail}")


def required(name, ok, detail):
    report("ok" if ok else "FAIL", name, detail)
    if not ok:
        failures.append(name)


def later(name, ok, detail):
    report("ok" if ok else "not yet", name, detail)


def run(cmd):
    if not shutil.which(cmd[0]):
        return None, "not on PATH"
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    return r.returncode, (r.stdout.strip() or r.stderr.strip())


required("python", sys.version_info >= (3, 9), sys.version.split()[0] + " (need 3.9 or later)")

code, out = run(["node", "--version"])
required("node", code == 0, out if code == 0 else "Node.js is needed by the CDK CLI: " + out)

code, out = run(["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"])
required("aws credentials", code == 0, f"account {out}" if code == 0 else out)

code, out = run(["aws", "configure", "get", "region"])
required("aws region", code == 0 and bool(out), out if code == 0 and out else
         "no region configured: set AWS_REGION or a region in your profile")

code, out = run(["cdk", "--version"])
later("cdk cli", code == 0, out if code == 0 else "installed in lesson 00")

for module in ("aws_cdk", "boto3", "pytest"):
    try:
        __import__(module)
        later(module, True, "importable")
    except ImportError:
        later(module, False, "installed into .venv in lesson 00")

sys.exit(1 if failures else 0)
