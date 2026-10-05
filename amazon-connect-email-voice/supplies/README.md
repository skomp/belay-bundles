# Contact centre

An Amazon Connect contact centre, built up lesson by lesson as an AWS CDK app in
Python: an inbound email address first, then a phone line on the same routing.

## Layout

- `app.py` — the CDK entry point. It creates the two stacks below and nothing else.
- `contact_centre/core_stack.py` — **ConnectCore**, the long-lived stack: the
  instance, the email address and the phone number. Deployed rarely.
- `contact_centre/routing_stack.py` — **ConnectRouting**, the churning stack:
  hours, queues, routing profiles, flows, the lookup Lambda and its table.
  Redeployed freely.
- `flows/` — contact flows exported from the console flow designer, with every
  ARN replaced by a placeholder. The file is the flow; the console is where you
  draw it.
- `lambdas/` — the lookup Lambda's code.
- `tests/` — pytest tests against the synthesized templates. No AWS account needed.
- `checks/` — the checks the tutor runs against your deployed contact centre.
  They read it back from your AWS account; they never change anything.
- `tools/`, `data/` — helpers and seed data a lesson hands you when it needs them.

## Working with it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cdk synth                     # does it build?
python3 -m pytest -q tests    # does it declare what you meant?
cdk deploy ConnectCore        # rarely
cdk deploy ConnectRouting     # as often as you like
```

The account and region come from your AWS configuration (`AWS_PROFILE`,
`AWS_REGION`), never from this code.

## Tearing it down

Release the phone number, then `cdk destroy ConnectRouting`, then
`cdk destroy ConnectCore`. The full order, and why, is in `tutorial/COURSE.md`
under *When you are finished*. A contact centre left running keeps costing money.
