# Amazon Connect: an Email-and-Voice Contact Centre as Code

**Bundle id:** `amazon-connect-email-voice`
**Scale:** standard — nine lessons, several sittings, chapters without milestone ceremony
**Status:** approved by the author 2026-10-05
**Date:** 2026-10-05

## The learner

For an engineer who is fluent in AWS — IAM, Lambda, DynamoDB, the CLI, and at least some
infrastructure as code — and who has **never worked with a contact centre**. Queues, routing
profiles, contact flows, agent states and channel concurrency are all new. AWS itself is not
taught: a learner who needs IAM explained is in the wrong course.

At the end they have one AWS CDK (Python) app that deploys a working Amazon Connect contact
centre: an inbound email address and a claimed phone number, both feeding the same hours,
queues and routing profiles, with a Lambda that looks the customer up and enriches every
contact. They can take any contact — an email or a call — and trace it from arrival to the
agent who received it, explaining each routing decision on the way from the evidence.

**One sentence:** send an email or ring the number, and it lands with the right agent in the
right queue — and you can show exactly why, from the contact record.

## The arc

Email first, then voice. Email is the cheaper, slower channel to learn routing on: no number
to rent, no per-minute charge, and a contact that waits patiently while the learner reads the
console. Voice then arrives as a second channel onto routing the learner already understands,
which isolates what is channel-specific from what is shared.

| # | slug | purpose | objective | instructive failure | completion | design_refs | validators |
|---|---|---|---|---|---|---|---|
| 00 | `instance-and-first-agent` | stand up a Connect instance from code and get a human logged into it | the Connect instance; identity management; security profiles vs routing profiles; agent users; the agent workspace | choosing an identity mode or alias without realising neither can change after creation; giving the agent a security profile and expecting it to decide which contacts they get; putting the instance in the same stack as everything that will churn | the long-lived stack deploys, the instance and an agent user exist, and the learner logs into the agent workspace and sets the agent Available | `#instance-choices`, `#stack-split` | `cdk-synth`, `pytest`, `instance-live` |
| 01 | `first-email-contact` | get one real email from the learner's own mailbox to the agent and answered | the email channel; email addresses on the instance's `email.connect.aws` domain; inbound flows; the contact as Connect's unit of work; the flow designer and its export | creating the address but never associating an inbound flow with it; an agent whose routing profile does not include the email channel, so the contact queues and nobody is offered it; editing the flow in the console after exporting, so the next deploy silently reverts it | an email the learner sends arrives as a contact, is offered to and accepted by their agent, and the reply reaches their mailbox; the flow lives in `flows/` and deploys from there | `#flow-round-trip`, `#stack-split` | `cdk-synth`, `pytest`, `email-routed` |
| 02 | `hours-queues-routing-profiles` | route on purpose instead of into the default queue | hours of operation; queues; routing profiles and channel concurrency; how hours, queue, routing profile and agent compose | expecting a queue's hours to stop contacts arriving rather than branch the flow; a routing profile that names the queue but not the channel; testing out-of-hours by waiting instead of by changing the hours | email to the address lands in the course's own queue during hours and takes the out-of-hours branch outside them, demonstrated both ways on demand | `#flow-round-trip` | `cdk-synth`, `pytest`, `email-routed` |
| 03 | `flow-logic-for-email` | make the flow decide something | contact attributes (system vs user); branching; setting the working queue; email-specific blocks such as an automatic acknowledgement | branching on an attribute that was never set, which falls through to the default branch silently; reaching for a voice-only block in an email flow; hard-coding a queue ARN into the exported JSON instead of a placeholder | an email whose subject or sender matches a rule is acknowledged automatically and routed to a different queue than one that does not, and the decision is visible on the contact's attributes | `#flow-round-trip` | `cdk-synth`, `pytest`, `email-routed` |
| 04 | `lambda-enrichment` | let the flow know who is writing | invoking Lambda from a flow; the event Connect sends and the response it accepts; Connect's permission to invoke; timeouts and the error branch; DynamoDB lookup | forgetting the Lambda association, so the block fails at run time and not at deploy; returning a nested object Connect will not accept; no error branch, so a Lambda timeout strands the contact; keying the lookup on something only email has | a known sender's email is routed to the priority queue with customer attributes set by the Lambda; an unknown sender and a deliberately failing Lambda each take their own branch | `#lambda-contract`, `#flow-round-trip` | `cdk-synth`, `pytest`, `lambda-enriches` |
| 05 | `following-a-contact` | explain where a contact went from the evidence, not from memory | contact search; contact records and attributes; flow logs in CloudWatch; Lambda logs correlated by contact id | reading the flow to guess what happened instead of reading the log of what did; enabling flow logging after the contact you wanted to inspect; trusting the agent workspace's view as the routing record | the learner is handed three contacts the supplied scenario script created and, for each, names the branch it took, the queue it reached and the attribute that decided it, citing the log line or record field | `#lambda-contract` | `contact-explained` |
| 06 | `a-phone-line` | add voice as a second channel onto the routing that already exists | claiming a phone number, and why its country is independent of the instance's region; voice inbound flows; prompts; what is shared across channels (hours, queues, routing profiles) and what is not | claiming the number in the churning stack so a redeploy releases it; reaching for a number in the learner's own country and stalling on a regulatory support case, when the course's US DID needs none; assuming the email flow can serve voice; forgetting the agent's routing profile has no voice concurrency | a call to the claimed number is answered by the voice flow, routed through the same hours and queue as email, and accepted by the agent in the workspace | `#stack-split`, `#instance-choices`, `#flow-round-trip` | `cdk-synth`, `pytest`, `call-routed` |
| 07 | `voice-menu-and-caller-lookup` | give callers a menu and recognise them | Get customer input; DTMF; timeouts and the no-input branch; reusing the lesson 04 Lambda keyed on the caller's number | no timeout branch, so a silent caller loops or drops; writing a second Lambda for voice instead of honouring the contract; normalising the phone number in the flow instead of in one place | a known caller is greeted and routed to the priority queue by the same Lambda that serves email, a menu choice changes the queue, and a caller who presses nothing reaches the agent anyway | `#lambda-contract`, `#flow-round-trip` | `cdk-synth`, `pytest`, `lambda-enriches`, `call-routed` |
| 08 | `one-agent-two-channels` | decide what an agent is offered when both channels are busy | routing-profile concurrency across voice and email; cross-channel behaviour; queue priority and delay; what the agent workspace shows for each | expecting an agent on a call to be offered nothing else, or everything else, without having configured it; priorities set on the queue when the intent was per channel; testing with one contact at a time and concluding it works | with a call and two emails waiting, the agent is offered them in the order the learner predicted before testing, and the learner explains the ordering from the routing profile | `#stack-split` | `cdk-synth`, `pytest`, `concurrency-observed` |

Every completion condition depends only on what earlier rows built: lesson 04's Lambda is
reused by 07, lesson 05 inspects contacts that the flows of 01–04 route, and lesson 06's
number is claimed in the long-lived stack lesson 00 established.

**Teardown is not a lesson.** Releasing the number and deleting the instance teach nothing a
learner can get wrong instructively, but forgetting them costs money. It is a closing section
in `COURSE.md`, and the cost entry in *Coverage* points at it.

## Chapters

- **Chapter 1 — a contact centre that exists** (00)
- **Chapter 2 — email, end to end** (01–04)
- **Chapter 3 — seeing what happened** (05)
- **Chapter 4 — voice on the same routing** (06–08)

## Teaching stance

```yaml
workspace_kind: new-repository
tutor_owned:   [tutorial/STATE.md, tutorial/DESIGN.md]
learner_owned:
  - app.py
  - contact_centre/**
  - flows/**
  - lambdas/**
  - tests/**
  - cdk.json
  - requirements.txt
  - requirements-dev.txt
  - README.md
ownership_policy: tutor-must-not-edit-learner-owned
one_task_at_a_time: true
solution_code: on-request-only
advance_on: validated-evidence-only
```

**Live state is checked from the AWS account, not taken on the learner's word.** The
analogue of `orange-pi-network-appliance` checking a board over SSH: supplied check scripts
call the Connect APIs with the learner's credentials and read the instance, the address, the
flow associations and — after a test contact — the contact record itself. A stack that
synthesizes but was never deployed must not pass, and a flow that deploys but routes to the
wrong queue must not pass either.

**Validators are the tutor's to run, never the learner's.** A lesson names the validator, not
a runnable command, following the correction recorded in
`orange-pi-network-appliance/SPEC.md`. Sending the test email and placing the test call stay
the learner's imperative steps; the checks then read the contact they produced.

```yaml
validators:
  toolchain-present:    { kind: command, command: [python3, checks/toolchain.py] }
  cdk-synth:            { kind: command, command: [cdk, synth, --quiet] }
  pytest:               { kind: command, command: [python3, -m, pytest, -q, tests] }
  instance-live:        { kind: command, command: [python3, checks/live.py, instance] }
  email-routed:         { kind: command, command: [python3, checks/live.py, email] }
  lambda-enriches:      { kind: command, command: [python3, checks/live.py, lambda] }
  call-routed:          { kind: command, command: [python3, checks/live.py, call] }
  contact-explained:    { kind: manual }
  concurrency-observed: { kind: manual }

setup_validators:
  - name: toolchain-present
    describe: Checks that Python, Node, the CDK CLI and AWS credentials for one account are available, so a failure in lesson 00 is your code and not your environment.
```

`contact-explained` and `concurrency-observed` are manual on purpose: the evidence is the
learner's explanation and a prediction made before the test, which no API call can grade.

## Supplied files

| from | to | describe | scope |
|---|---|---|---|
| `supplies/app.py` | `app.py` | The CDK entry point with two empty stacks — the long-lived one and the one you redeploy freely — so lesson 00 starts at the instance and not at CDK boilerplate | `tutorial.yaml` |
| `supplies/cdk.json` | `cdk.json` | CDK settings that point at `app.py`; nothing in this course changes it | `tutorial.yaml` |
| `supplies/requirements.txt` | `requirements.txt` | The CDK libraries this app deploys with | `tutorial.yaml` |
| `supplies/requirements-dev.txt` | `requirements-dev.txt` | pytest and boto3, for the template tests and the live checks | `tutorial.yaml` |
| `supplies/conftest.py` | `tests/conftest.py` | A fixture that synthesizes both stacks into templates your tests assert against | `tutorial.yaml` |
| `supplies/README.md` | `README.md` | How this app is laid out, deployed and torn down | `tutorial.yaml` |
| `supplies/gitignore` | `.gitignore` | Keeps `cdk.out`, the virtualenv and editor droppings out of your history | `tutorial.yaml` |
| `supplies/checks-toolchain.py` | `checks/toolchain.py` | The check that confirms your toolchain and AWS credentials before you start | `tutorial.yaml` |
| `supplies/checks-live.py` | `checks/live.py` | The checks that read your deployed contact centre and its contacts back from AWS | `tutorial.yaml` |
| `lessons/04-lambda-enrichment/customers.json` | `data/customers.json` | A handful of fictional customer records, with example-domain email addresses and reserved phone numbers, for the lookup table — writing seed data teaches nothing | `04-lambda-enrichment` |
| `lessons/05-following-a-contact/scenarios.py` | `tools/scenarios.py` | Creates three test email contacts through the Connect API, each built to take a different path through your flow, for you to explain | `05-following-a-contact` |

The check scripts are supplied for the reason `pico-ps2-usb-adapter` gives: writing a Connect
API reader is not what this course teaches, and a validator the learner wrote is a validator
the learner can satisfy by weakening. The seed data uses fictional records only — no real
personal data appears anywhere in the bundle. To be recognised in lessons 04 and 07 the
learner adds a record with their own email address and phone number to the table in their
own account; the lesson says so, and says that this is their personal data in their account
and is deleted at teardown. Their caller ID will usually be a non-US number in E.164 form,
which is exactly the case `#lambda-contract`'s normalisation has to handle.

**Not supplied, and deliberately so:** every construct, flow and Lambda. Installing the CDK
CLI, creating the virtualenv, configuring AWS credentials and running `cdk bootstrap` need
the network and an account, so they are the learner's own setup inside lesson 00's
progression, not a lesson and not a supply.

## Durable decisions

### instance-choices

The instance uses `CONNECT_MANAGED` identity, so users live in Connect and no directory or
SAML provider is needed. One region is chosen in lesson 00 and used for everything; it must
support the email channel. The instance alias follows one convention
(`<learner-prefix>-tutorail-cc`) because it is globally unique and becomes the email domain.

**The phone number is a US direct-dial (DID) number, whatever the instance's region.** Since
July 2023 an instance can claim numbers outside its own region with no opt-in, and a US DID is
claimed self-service with no documents. Many countries are not like that: Germany, for one,
can require a local address and identity documents through an AWS Support case before a
number is issued. A course that told each learner to claim a number in their own country
would stall a large share of them at lesson 06 for days, on paperwork that teaches nothing
about Connect. So the instance region stays the learner's choice — an EU region is a
reasonable one for a learner in the EU — and the number is always US. The cost a learner pays
for that is an international call from their own phone for each test, named in *Coverage*.

What breaks if a lesson contradicts it: identity mode and alias cannot change after creation,
so a wrong choice means deleting the instance and every contact in it. A region without
email stalls lesson 01 with no fix short of starting over. A lesson that assumes a local
number reintroduces the regulatory stall. Resolved, with the region list itself an open
question below.

### stack-split

Two stacks. The **long-lived** stack holds the instance, the email address and the claimed
phone number. The **churning** stack holds hours, queues, routing profiles, flows, the
Lambda and the table, and is redeployed freely. Cross-stack references pass ARNs one way,
from long-lived to churning.

What breaks if a lesson contradicts it: a phone number in the churning stack is released by a
replacement and may never be reclaimable; an instance that is recreated loses its alias, its
email domain and its contact history. Resolved.

### flow-round-trip

Flows are designed in the console flow designer, exported as JSON into `flows/`, and deployed
from there by CDK. Every ARN in the exported JSON — queues, Lambda, prompts — is replaced
with a placeholder that the stack substitutes at synth. The repository is the source of
truth: a console edit that is not exported is overwritten by the next deploy, and that is
intended.

What breaks if a lesson contradicts it: a flow with a hard-coded ARN deploys only into the
account it was exported from and breaks the first time a queue is replaced; a learner who
edits in the console and deploys loses the edit and learns to distrust the tooling. Resolved.

### lambda-contract

One lookup Lambda serves both channels. Input: the contact's customer endpoint — an email
address or an E.164 phone number — taken from the Connect event. Output: a flat map of string
attributes (`customer_id`, `tier`, `display_name`), or an empty map for an unknown customer.
Errors raise, so the flow's error branch handles them.

What breaks if a lesson contradicts it: lesson 07 reuses the function unchanged; a contract
shaped around email in lesson 04 forces a second Lambda or a breaking change mid-course.
Connect also rejects a nested response. Resolved.

### Deliberately unresolved

- **Custom email domain.** The course uses the instance's automatic `email.connect.aws`
  domain. Moving to a domain verified in SES is named in *Coverage* and never built.
- **Agent concurrency numbers.** Lesson 08 asks the learner to choose and defend them; the
  course does not prescribe values.

## Coverage

The course owes a learner, even where the build does not force them:

- `cost and teardown` — what bills per message, per minute and per day of number rental;
  what keeps billing after the course; releasing the number and deleting the instance; and,
  for a learner outside the US, that each test call to the US number is an international call
  from their own phone
- `phone number regulation` — why numbers in some countries need documents and a support
  case, why the course claims a US number instead, and what a production contact centre in
  such a country would have to do
- `ses sandbox` — why replies to an unverified address fail in a new account, and the
  request that lifts it
- `security profiles and least privilege` — what an agent profile should and should not
  grant
- `personal data in contacts` — email bodies, attachments and contact attributes as personal
  data; retention, encryption with KMS, and what not to put into an attribute
- `ai agents and q in connect` — what generative self-service and agent assist add to a flow
  like the learner's, named and explained, not built

Deliberately **not** taught: chat and tasks as channels; outbound campaigns; call recording
and Contact Lens analytics; Lex bot authoring; SAML or directory identity; custom agent
desktops with the Streams API; custom email domains; multi-region resilience; AWS
fundamentals (IAM, Lambda, CDK basics), which the course assumes.

## Proposed manifest fields

```yaml
bundle_format: 1
id: amazon-connect-email-voice
title: "Amazon Connect: an Email-and-Voice Contact Centre as Code"
description: >
  Build an Amazon Connect contact centre with AWS CDK in Python: an inbound email
  address first, then a phone line on the same queues and routing, with a Lambda that
  recognises the customer on either channel.
teaching_method: >
  You write every construct, flow and Lambda yourself; the tutor checks your deployed
  contact centre and the contacts it routed, straight from your AWS account.
subjects: [aws, amazon-connect, contact-centre, infrastructure-as-code, lambda]
aliases: [connect, aws-connect, call-centre, call-center, contact-center, ivr, email-routing, cdk]
level: intermediate
style: [project-driven, interactive]
```

The title contains `": "` and is quoted, per the toolkit trap recorded in this repository's
`CLAUDE.md`.

## Open questions

- **Which regions to recommend.** The email channel is not in every Connect region. To be
  checked against the AWS documentation when lesson 00 is written, not assumed — including
  whether claiming a US DID from each recommended region (an EU one in particular) works
  self-service, which the July 2023 change suggests but this spec has not verified per region.
- **A cheaper way to place the test call.** Whether a learner outside the US can reach the
  number without an international call — for example a VoIP app with a US calling rate — is
  worth a line in lesson 06 if a reliable option exists. Not required for the course to work.
- **Whether enabling email on an instance is fully expressible in CloudFormation**, or needs
  one console or API step in lesson 02. `AWS::Connect::EmailAddress` exists; whether the
  instance's email domain is provisioned without a console action is to be verified when
  lesson 01 is written. If it is not, the step stays the learner's work in that lesson and
  the spec is revised.
- **Whether CDK's `CfnContactFlow` accepts email flows** with the content placeholders
  `#flow-round-trip` needs, or whether a flow type or module constraint applies. Verify
  before lesson 01 is filled.

This spec has passed the authoring self-check — a first filter, not a proof. Only walking the
course finds the rest.

## Revision note

2026-10-05, after approval: lesson numbers shifted down by one (00 to 08) to match the toolkit, which numbers from 00 like every other bundle in this repository. Slugs, order and content are unchanged.
