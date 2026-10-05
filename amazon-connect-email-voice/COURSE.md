# Amazon Connect: an Email-and-Voice Contact Centre as Code

## The goal

You will build a working Amazon Connect contact centre from one AWS CDK app in Python. It
has an inbound email address and a phone number, both feeding the same hours, queues and
routing profiles, and a Lambda that recognises the customer on either channel and sends the
ones who matter to a priority queue. You are the agent: you log in, accept the email or the
call, and answer it.

The point is not the finished stack. It is that by the end you can take any contact — an
email or a call — and trace it from arrival to the agent who received it, explaining every
routing decision on the way from the evidence: the contact record, the flow log, the Lambda
log. Not from what you remember writing.

## How this course teaches

**Email first, then voice.** Email is the gentler channel to learn routing on: no number to
rent, no per-minute charge, and a contact that waits patiently in the queue while you read
the console. Voice then arrives as a second channel onto routing you already understand, and
that is what shows you which parts of a contact centre are channel-specific and which are
shared.

You write every construct, every flow and the Lambda yourself. Flows you draw in the
console's flow designer, export, and keep in your repository; from then on the file is the
flow (see `DESIGN.md`, *Flow round trip*).

The tutor reads your deployed contact centre back from your AWS account through small check
scripts — the instance, the address, which flow it runs, and the contact record your test
email actually produced. It never advances on "it works for me".

## What this course assumes you have

- **AWS fluency.** IAM, Lambda, DynamoDB, CloudWatch Logs and the AWS CLI. This course
  teaches Amazon Connect, not AWS.
- **AWS CDK in Python**, at the level of having written and deployed a small app. The CDK CLI
  needs Node.js.
- **An AWS account you may create billable resources in**, with credentials configured for
  one account and one region. Installing the toolchain, configuring credentials and running
  `cdk bootstrap` need the network and your account, so they are your work in lesson 00.
- **An email mailbox you can send from and receive at**, and **a phone that can call a US
  number.** The course claims a US number on purpose (see `DESIGN.md`, *Instance choices*);
  from outside the US each test call is an international call.

## The chapters, in order

### Chapter 1 — a contact centre that exists

- **00 — Instance and first agent.** Deploy the instance from code, create an agent, log in
  and go Available.

### Chapter 2 — email, end to end

- **01 — First email contact.** An email address, an inbound flow, and your own email
  answered by your own agent.
- **02 — Hours, queues, routing profiles.** Route on purpose instead of into the default
  queue, with an out-of-hours branch.
- **03 — Flow logic for email.** Attributes, branching, an automatic acknowledgement and a
  second queue.
- **04 — Lambda enrichment.** The flow asks a Lambda who is writing; known customers go to
  the priority queue.

### Chapter 3 — seeing what happened

- **05 — Following a contact.** Explain three contacts you did not route by hand, from the
  contact record and the logs.

### Chapter 4 — voice on the same routing

- **06 — A phone line.** Claim a US number and route calls through the hours and queues email
  already uses.
- **07 — Voice menu and caller lookup.** A menu, timeouts, and the same Lambda recognising
  callers.
- **08 — One agent, two channels.** Decide what an agent is offered when a call and emails
  wait at once.

## How long it takes

Rough hands-on time for an AWS-fluent learner new to contact centres. Deploys are the slow
part; a new instance takes a few minutes to become usable.

| Segment | Time |
|---|---|
| Chapter 1 — toolchain, bootstrap, instance and agent (00) | 1–1.5 h |
| Chapter 2 — email end to end (01–04) | 3–4.5 h |
| Chapter 3 — following a contact (05) | 0.75–1 h |
| Chapter 4 — voice (06–08) | 2.5–3.5 h |
| **Whole course** | **≈ 7–10.5 h** |

## Coverage

Topics this course owes you, even where the build does not force them. The tutor treats a
question on any of these as in scope.

- **cost and teardown** — what bills per email, per minute and per day of number rental;
  what keeps billing after the course; releasing the number and deleting the instance (see
  *When you are finished*); and, from outside the US, that each test call is an
  international call.
- **phone number regulation** — why numbers in some countries need documents and a support
  case, why the course claims a US number instead, and what a production contact centre in
  such a country would have to do.
- **ses sandbox** — why replies to an unverified address can fail in a new account, and the
  request that lifts it.
- **security profiles and least privilege** — what an agent's security profile should and
  should not grant, and why it is not what decides which contacts they get.
- **personal data in contacts** — email bodies, attachments and contact attributes are
  personal data; retention, encryption with KMS, and what never to put into an attribute.
- **ai agents and q in connect** — what generative self-service and agent assist would add
  to a flow like yours. Explained, not built.

Deliberately **not** taught: chat and tasks as channels; outbound campaigns; call recording
and Contact Lens analytics; Lex bot authoring; SAML or directory identity; custom agent
desktops with the Streams API; custom email domains; multi-region resilience; and AWS
fundamentals — IAM, Lambda, CDK basics — which the course assumes. A learner stuck on one of
these has stepped outside the course, not hit a gap in it.

## When you are finished

A contact centre left running keeps costing money. When you are done — or pausing for more
than a few days — tear it down in this order:

1. **Release the phone number** first. It bills daily, and a number deleted with the stack
   is released the same way; doing it deliberately means you know it is gone.
2. **Destroy the churning stack**, then the **long-lived stack**. Deleting the instance
   deletes its contacts, users and email address.
3. **Delete the customer record you added with your own email address and phone number**, if
   anything kept it — the table goes with the churning stack, but a copy in a file of yours
   does not.
4. Check the Connect console in your region shows no instance, and the billing console shows
   no claimed numbers.
