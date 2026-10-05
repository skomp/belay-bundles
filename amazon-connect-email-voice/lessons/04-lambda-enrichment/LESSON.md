---
id: 04-lambda-enrichment
title: Lambda enrichment
design_refs: [lambda-contract, flow-round-trip]
validators: [cdk-synth, pytest, lambda-enriches]
supplies:
  - from: lessons/04-lambda-enrichment/customers.json
    to: data/customers.json
    describe: Fictional customer records for the lookup table; writing seed data teaches nothing
---

## Purpose

Let the flow know who is writing: a Lambda looks the sender up in DynamoDB, the flow copies what it returns onto the contact, and known gold customers go to the priority queue.

A flow can only branch on what it knows, and so far it knows the email itself — subject,
sender address, the time it arrived. It does not know that the sender is a customer, or an
important one. That knowledge lives in your systems, and a flow reaches your systems by
calling a Lambda. This lesson builds the one lookup Lambda the course has: written once for
email, but shaped by `#lambda-contract` so that lesson `07-voice-menu-and-caller-lookup` can
reuse it **unchanged** for callers. Getting the contract right now is the point. A function
that only works for email is a second Lambda, or a breaking change, three lessons from now.

## Prerequisites

- Lesson `03-flow-logic-for-email`: the priority queue (output `PriorityQueueId`,
  placeholder `${PriorityQueueArn}`) in the agent's routing profile; the subject branch; the
  `route_reason` attribute set on every path; the guard test that keeps `arn:aws:` out of
  `flows/inbound-email.json`.
- The flow round trip from lesson `01-first-email-contact` and the placeholder map passed to
  `Fn.sub`.
- AWS Lambda, DynamoDB and IAM at working level — this lesson teaches how Connect calls a
  function, not how to write one.

When this lesson opens, two files arrive in the workspace: `data/customers.json`, a handful of
**fictional** customer records, and `tools/load_customers.py`, which writes those records
into the table. Writing seed data and a loader teaches nothing about Connect, so they are
supplied — they ship beside this lesson file as `customers.json` and `load_customers.py`, and
the runner places them. The learner runs the loader; they do not write or copy it.

## Learning objectives

- Explain what Connect sends a Lambda (`Details.ContactData`, `Details.Parameters`) and
  what it accepts back, and pick the customer endpoint from `CustomerEndpoint.Address`.
- Write a handler that serves **both channels** under `#lambda-contract`: one normalisation
  function, branching on `Channel`, a flat string map out, an empty map for an unknown
  customer, an exception for a failure.
- Grant Connect the right to call it — the instance integration association **and** the
  function's resource-based permission — and say which one CloudFormation does not create
  for you.
- Configure the **AWS Lambda function** block: synchronous, a timeout under 8 seconds,
  response validation `STRING_MAP`, and an Error branch wired to somewhere sensible.
- Copy returned values onto the contact with **Set contact attributes** so they survive into
  the contact record, and branch on `tier`.
- Unit-test the handler with fake email **and** voice events, without AWS.

## Theory

### How a flow calls a Lambda

The **AWS Lambda function** block (in the designer's Integrate group) invokes a function with
an event Connect builds for the contact. The parts that matter here:

```text
event["Details"]["ContactData"]["Channel"]                 # "VOICE" | "CHAT" | "TASK" | "EMAIL"
event["Details"]["ContactData"]["ContactId"]
event["Details"]["ContactData"]["CustomerEndpoint"]["Address"]
event["Details"]["ContactData"]["Attributes"]              # user-defined attributes so far
event["Details"]["Parameters"]                             # what the block was told to pass
event["Name"]                                              # "ContactFlowEvent"
```

`CustomerEndpoint.Address` is the sender's address on an email contact and the caller's number
on a call. `CustomerEndpoint.Type` is documented as `TELEPHONE_NUMBER` for calls; **what it is
for an email contact is not documented.** So the handler never branches on `Type`. It branches
on `Channel`, which is documented for both. That is a rule of `#lambda-contract`, and the reason
is exactly this gap in the documentation.

The block runs in one of two modes. **Synchronous** waits for the function before the contact
moves on, with a timeout of at most **8 seconds**; **asynchronous** does not wait, allows up to
60 seconds, and needs a separate step to load the result. A lookup that decides routing is
synchronous. The function's own Lambda timeout stays below the block's, so the function never
outlives the wait.

### What Connect accepts back

The block has a **Response validation** setting. With **`STRING_MAP`**, the function must return
a flat object whose values are strings — `{"customer_id": "C-1001", "tier": "gold", ...}`. With
`JSON`, nested objects are allowed. This course uses `STRING_MAP` (`#lambda-contract`) because it
is the strictest contract: if the function returns something Connect does not understand, the
contact goes down the **Error** branch, *at run time*, contact by contact. A nested object with
`STRING_MAP` is precisely such a response. No deploy, synth or unit test of the flow catches it —
only a unit test of the *handler's output shape* does.

The documentation also says the returned values may contain only alphanumeric characters,
dashes and underscores. That is stricter than it sounds for `display_name` ("Ada Lovelace" has a
space). Treat it as something to find out on your own instance: return a display name with a
space, and read what the contact record and the flow log show. Record the result.

An unknown sender is not an error. The function returns `{}`; the flow continues on its Success
branch with no customer attributes, and the tier check falls through. Errors — the table cannot
be read, the event is malformed — **raise**. When a synchronous invocation returns an error,
Connect retries it up to three times within the timeout and then takes the Error branch. A
function that catches its own failure and returns a made-up customer hides the failure from the
flow; `#lambda-contract` forbids it.

### Returned values are not contact attributes until you copy them

Right after the block, the response is readable as **External** attributes: `$.External.tier`.
Those values are overwritten by the next Lambda call and are **not** stored in the contact
record. To keep them — and the course needs them on the contact for lesson
`05-following-a-contact` and for the check this lesson ends with — a **Set contact attributes**
block copies each one to a **User-defined** attribute on the current contact: `customer_id`,
`tier`, `display_name`. Branch on the copy, `$.Attributes.tier`, and you branch on the same value
the record will show.

Notice what happens to an unknown customer: the copy of `$.External.tier` has nothing to copy,
and a Check contact attributes for `tier` **Equals** `gold` takes **No match**. That is the
lesson `03-flow-logic-for-email` failure — an attribute that was never set — and here it is the
intended path. Be sure which one you are looking at.

### Two grants, and the one CloudFormation does not make

Connect needs two separate things before a flow may call a function:

1. **An integration association** on the instance — `AWS::Connect::IntegrationAssociation`
   with `IntegrationType` `LAMBDA_FUNCTION`, `InstanceId` the instance **ARN**, `IntegrationArn`
   the function ARN. This is what makes the function selectable in the designer.
2. **A resource-based permission** on the function — principal `connect.amazonaws.com`, source
   account your account, source ARN your instance's ARN. This is what lets Lambda accept the
   invoke.

When you add a function in the Connect console, the console creates the second one for you.
CloudFormation does **not**: declaring the association alone leaves Connect unable to invoke the
function. The SPEC expects a missing grant to show up as a failed block at run time rather than
a failed deploy; find out on your own instance which grant fails how, and record it.

Scope the permission to the instance ARN. A permission for `connect.amazonaws.com` with no source
ARN lets any Connect instance, in any account, invoke your function.

### Keyed on something both channels have

The table's partition key is `endpoint`: a **lower-cased, trimmed email address** or an
**E.164 phone number** (`+` followed by digits). The handler turns `CustomerEndpoint.Address`
into that key in **one function**, which branches on `Channel`. Lesson
`07-voice-menu-and-caller-lookup` feeds the same function a caller's number; the learner's own
caller ID will usually be a non-US number, which is exactly the case that normalisation exists
for. Normalising in the flow, or keying on something only an email has (the subject, the display
name, the domain), breaks that reuse.

## Concepts to teach

- **The Connect Lambda event**: `Details.ContactData.{Channel, ContactId,
  CustomerEndpoint.Address, Attributes}`, `Details.Parameters`; `CustomerEndpoint.Type`
  undocumented for email, so branch on `Channel`.
- **Synchronous invocation**: at most 8 seconds, function timeout below it; retries on error,
  then the **Error** branch.
- **`STRING_MAP` response validation**: flat map of strings; a nested object takes Error at run
  time; `{}` for an unknown customer; errors raise.
- **External vs user-defined attributes**: `$.External.*` is transient and not in the contact
  record; Set contact attributes copies it onto the contact.
- **The two grants**: `AWS::Connect::IntegrationAssociation` (`LAMBDA_FUNCTION`, instance ARN)
  and a Lambda permission for `connect.amazonaws.com` scoped by source account and instance ARN;
  the console adds the permission, CloudFormation does not.
- **One normalisation function** keyed on `Channel`, producing the table's `endpoint` key for
  both channels.
- **Every branch accounted for**: Success with a customer, Success with `{}`, Error (and a
  Timeout branch if the block shows one).
- **Personal data**: the learner's own email address in their own table is their personal data,
  added on purpose, removed at teardown.

## Constraints

- The learner writes the handler, its tests and every construct. The tutor states what they must
  do and checks the result; it does not write them. `data/customers.json` and
  `tools/load_customers.py` are supplied and only run.
- The function's code lives in `lambdas/lookup/`, in Python, and the function and table live in
  `ConnectRouting`, published as **`LookupFunctionName`** and **`CustomersTableName`**.
- The table's partition key is `endpoint` (string); items hold `customer_id`, `tier` (`gold` or
  `standard`) and `display_name`.
- The handler follows `#lambda-contract` exactly: endpoint from `CustomerEndpoint.Address`;
  normalisation in one function; branch on `Channel`, never on `CustomerEndpoint.Type`; a flat
  map of strings out, `{}` for unknown, exceptions for errors; no fake customer on failure.
- The handler logs the contact id (`Details.ContactData.ContactId`) on every invocation, in a
  line that also says what it looked up and what it found. Lesson `05-following-a-contact`
  correlates Lambda logs with contacts through it. It never logs a whole event.
- The function has read-only access to its table, nothing more. Its timeout is below 8 seconds.
- The integration association and the Lambda permission are both declared in CDK. The permission
  names `connect.amazonaws.com`, the source account, and the instance ARN as source ARN.
- The flow block is synchronous with `STRING_MAP`, references the function only as
  `${LookupFunctionArn}`, and has its Error branch wired. The guard test from lesson
  `03-flow-logic-for-email` still passes.
- After the block, Set contact attributes copies `customer_id`, `tier` and `display_name` onto the
  current contact. A contact with `tier=gold` goes to the priority queue with
  `route_reason=tier-gold`. The learner decides, and records, which wins when a gold customer
  sends an urgent subject.
- The deliberate failure switch the learner builds is **off** when the lesson ends, and turning it
  on or off is one obvious step.

## Suggested progression

1. **Shape the contract in tests first.** The learner writes pytest tests for the handler before
   the handler, with hand-built fake events — no AWS, no network. The lookup is injected (a fake
   table or a lookup callable) so the tests run offline. At least: an email event for a known
   sender in mixed case and with stray whitespace finds the record; an email event for an unknown
   sender returns `{}`; a **voice** event with an E.164 `CustomerEndpoint.Address` finds a phone
   record; every value returned is a `str` and nothing is nested; a lookup failure raises. The
   voice test must pass in this lesson — lesson `07-voice-menu-and-caller-lookup` reuses the
   function unchanged and only adds a flow.
   *Instructive failure, let it happen if the learner reaches for it:* returning
   `{"customer": {"id": ..., "tier": ...}}` because it reads well. The shape test fails; ask what
   Connect would do with it under `STRING_MAP`, and where they would have found out otherwise.
   *Another, if they key on email only:* a normaliser that lower-cases and nothing else, or one
   that branches on `CustomerEndpoint.Type`. The voice test, or a fake email event with no
   `Type`, exposes it.
2. **Write the handler** until the tests pass. Keep normalisation in one function the tests can
   call directly. Add the contact-id log line.
3. **Add the table and the function** to `ConnectRouting`, with the outputs, read-only access,
   and a timeout below 8 seconds. Template tests: the table's key schema, the function's timeout,
   the outputs.
4. **Add the grants.** The integration association first, alone. Ask the learner to predict what
   happens when a contact reaches the block with only that. Then the Lambda permission, scoped to
   the instance ARN. Template tests for both, including that the permission carries a source ARN.
5. **Load the customers.** Deploy, then run `tools/load_customers.py` against the table. Then the
   learner adds **their own** record with the loader's `--add-endpoint <their address> --tier gold
   --name "<their name>"`. Say plainly: this is their personal data, in a table in their own
   account; it is there so their own email is recognised; `--remove-endpoint` deletes it, and
   teardown removes the table. It never goes into `data/customers.json` or into git.
6. **Wire the flow.** In the designer: the AWS Lambda function block (synchronous, timeout,
   `STRING_MAP`), then Set contact attributes copying the three values, then a Check contact
   attributes on `tier`. Gold sets `route_reason=tier-gold` and the priority queue. The Error
   branch goes somewhere the learner chooses and defends — usually the default routing with its
   own `route_reason` — never a dead end. Export, replace the function ARN with
   `${LookupFunctionArn}`, add it to the placeholder map, let the guard test confirm, deploy.
   *Instructive failure, if the learner skipped the Error branch:* ask what the contact does when
   the function times out. Step 8 shows it.
7. **Test the happy paths.** The learner emails from their own mailbox: their contact reaches the
   priority queue with `customer_id`, `tier=gold`, `display_name` and `route_reason=tier-gold`
   on the contact. The tutor runs `lambda-enriches`. Then the learner removes their record with
   `--remove-endpoint`, emails again, and the contact takes the unknown-customer path. Re-add the
   record afterwards; lesson `05-following-a-contact` does not need it, but lesson
   `07-voice-menu-and-caller-lookup` adds a phone number beside it.
8. **Break it on purpose.** The learner designs a failure switch for the function and builds it:
   for example an environment variable that makes the handler raise, set from CDK context, or a
   magic sender address that always raises. They choose, and say what each costs — an environment
   variable needs a redeploy to flip; a magic address needs none but lives in production code.
   With the switch on, an email takes the Error branch, and the learner finds the evidence: the
   function's CloudWatch log shows the invocations (count them — Connect retries), and the contact
   shows the Error path's `route_reason`. Then the switch goes **off**, and one more email proves
   the happy path is back.

## Completion conditions

- `cdk-synth` passes. `pytest` passes, including: handler tests for a known email sender
  (normalised from mixed case and whitespace), an unknown sender returning `{}`, a **voice** event
  with an E.164 number finding its record, a check that every returned value is a string and none
  is nested, and a failure that raises; template tests for the table key, the function timeout
  under 8 seconds, the integration association of type `LAMBDA_FUNCTION`, and a Lambda permission
  for `connect.amazonaws.com` with the instance ARN as source ARN.
- `ConnectRouting` publishes `LookupFunctionName` and `CustomersTableName`.
  `flows/inbound-email.json` references the function only as `${LookupFunctionArn}`, and the
  guard test passes.
- `lambda-enriches` passes for an email the learner sent from their own address: the contact
  reached the priority queue with `customer_id`, `tier=gold`, `display_name` and
  `route_reason=tier-gold` set as contact attributes.
- An email from an address not in the table took the unknown-customer path, and the learner shows
  its `route_reason` and queue from the contact record.
- With the failure switch on, an email took the Error branch; the learner shows the function's log
  lines for that contact id and the contact's `route_reason`. The switch is off again, and a later
  email routed normally.
- The learner can explain: why the handler branches on `Channel` and not on
  `CustomerEndpoint.Type`; why a nested response fails only at run time; which of the two grants
  CloudFormation does not create; why the values are copied with Set contact attributes; and what
  the voice test protects.

## On completion, persist

In the instance's `DESIGN.md`, under the lambda contract:

- The normalisation rules as implemented, for both email and E.164, and the function name that
  does it.
- The precedence chosen between `subject-urgent` and `tier-gold`, and the `route_reason` used for
  the Error path and for the unknown customer.
- What the learner observed about a `display_name` with a space under `STRING_MAP`.
- What the learner observed when only one of the two grants existed.
- How the failure switch works and how to turn it off.

In `STATE.md`: that the learner's own record is in the table (and therefore personal data exists
in their account until teardown); the contact ids of the gold, unknown and Error test emails; that
the failure switch is off.

## Optional deeper paths

- **Passing parameters.** The block's Function input parameters arrive in `Details.Parameters`. Is
  there anything the lookup should take from there rather than from `ContactData`? Usually not —
  discuss why.
- **Asynchronous invocation** with a later Load Lambda result step: where it would help (a slow
  CRM) and why routing on its result is awkward.
- **Cold starts and the 8-second budget.** Measure the function's first invocation after a deploy
  from its log, and compare it with the block's timeout.
- **Encrypting the table with a customer managed KMS key**, and what that changes in the
  function's permissions — part of the course's coverage of personal data in contacts.
- **Amazon Connect Customer Profiles** as the managed alternative to a home-made customer table:
  what it would replace, and what it would cost in setup.
