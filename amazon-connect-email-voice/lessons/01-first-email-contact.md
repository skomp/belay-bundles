---
id: 01-first-email-contact
title: First email contact
design_refs: [flow-round-trip, stack-split]
validators: [cdk-synth, pytest, email-routed]
---

## Purpose

Get one real email from your own mailbox to your agent, and get the agent's reply back to your mailbox.

Lesson `00-instance-and-first-agent` left an agent Available in an instance that nothing can
reach. This lesson gives the instance an inbound **email address**, writes your first **flow**
— drawn in the console's flow designer, exported, and deployed from your repository — and
joins the two. Three things have to be true at once for a single email to reach you, and each
fails silently: the address must have a flow associated with it, the flow must put the contact
in a queue, and your routing profile must offer that queue's email contacts to you. You will
see at least one of them fail before the email arrives. At the end you have answered your own
email from the agent's panel, and the flow that routed it lives in `flows/inbound-email.json`.

## Prerequisites

Lesson `00-instance-and-first-agent` complete: `ConnectCore` deployed with the instance and the
outputs `InstanceId`, `InstanceArn` and `InstanceAlias`; `ConnectRouting` deployed with your
agent user on the Basic Routing Profile; you can log in to the CCP and go Available, and you can
reach the admin website through **Log in for emergency access**. The region is in your AWS
configuration and supports email (`#instance-choices`).

You also need a mailbox you can send from and receive at. The email you send carries your own
address, and that is personal data in your AWS account (see *Constraints*).

## Learning objectives

- Describe how an email becomes a **contact**: what Connect receives, where the message is
  stored, which flow runs, and where the contact waits
- Enable the email channel for the instance, and say which part of that only the console can do
  and which part is code
- Declare the two storage configurations email needs (`EMAIL_MESSAGES`, `ATTACHMENTS`) and the
  email address `support@<alias>.email.connect.aws` in `ConnectCore`
- Draw a minimal inbound flow in the flow designer, export it, replace every ARN in it with a
  `${Name}` placeholder, and deploy it from `flows/inbound-email.json` (`#flow-round-trip`)
- Associate the flow with the address as an `AwsCustomResource` in `ConnectRouting`, and explain
  why that link lives in the churning stack (`#stack-split`)
- Check, rather than assume, that the agent's routing profile offers email from the queue the
  flow uses
- Explain the SES sandbox and decide whether your account's replies can reach your mailbox

## Theory

**How an email becomes a contact.** When the email channel is enabled, Amazon Connect receives
mail for its email addresses through Amazon SES. Each inbound email becomes a **contact** with
the channel `EMAIL`: the contact is the unit of work Connect routes, measures and records, and it
has an id, a start, an end and a contact record. The message itself — body and attachments — is
stored in Amazon S3, in the buckets the instance's storage configuration names. Connect then runs
the **inbound flow** associated with the email address the mail was sent to. The flow decides
what to do; for this lesson, it puts the contact in a queue. A routing profile that works that
queue *on the email channel* offers the contact to an Available agent, who accepts it, reads it
and replies. The reply is a contact too, sent out through SES.

**Email is asynchronous.** A caller hangs up if nobody answers. An email waits. An active email
contact stays open — waiting in a queue, or assigned to an agent — for 14 days by default before
it expires and closes, and that period can be extended to 90 days. This is why the course
learns routing on email first: a contact that waits patiently while you read the console is
forgiving. It is also why a mistake in routing is quiet. An email nobody is offered does not
bounce, does not error and does not ring; it simply sits in a queue.

**Enabling email has a console step.** Two parts of enabling email have no documented
CloudFormation or API form, so they are yours to do by hand, once: in the Connect console, on
your instance's **Email** page, choose **Create service role** (once per account; it lets SES
route email to Connect), then **Add domain** and pick the **Amazon Connect email domain**
option, which creates `<alias>.email.connect.aws`. The domain is derived from the alias and
cannot be changed — the reason lesson `00-instance-and-first-agent` treated the alias as
permanent. Recent AWS documentation also calls the product "Connect Customer"; the console may
use either name.

**The part that is code: storage.** Email needs two storage pointers to S3: one for email
messages and one for attachments. They may be the same bucket or two, and in CloudFormation each
is an `AWS::Connect::InstanceStorageConfig` with `ResourceType` `EMAIL_MESSAGES` or
`ATTACHMENTS`, `StorageType` `S3`, and an `S3Config` with a `BucketName` and a `BucketPrefix`.
The console's **Data storage** page can create the same configurations by hand. Do not let it:
in this course they are code. But whether the console's email step creates any storage
configuration by itself is not documented, so you check before you deploy (see *Suggested
progression*), and you decide what to do if one already exists. AWS also documents that if
attachments are enabled, the attachments bucket needs a **CORS policy** allowing `PUT` and `GET`,
for example from the origins `*.my.connect.aws`, or the email channel will not work.

The bucket holds every email anyone sends to your address — personal data. Treat it like it:
no public access, encryption, and a decision about retention, which for email messages is
governed by the bucket's lifecycle configuration. The bucket belongs in `ConnectCore`, beside
the instance it serves: it is long-lived state, not routing.

**The email address.** `AWS::Connect::EmailAddress` (`CfnEmailAddress`) takes the full
`EmailAddress`, the `InstanceArn`, and optionally a `DisplayName` and `Description`. Changing
the address itself requires replacement. The course's address is
`support@<alias>.email.connect.aws`, and it lives in `ConnectCore`, because it is the thing
customers write to and must not churn. Its `Ref` returns the address, and `attr_email_address_arn`
its ARN. Note what the resource does **not** have: any property naming the flow it runs.

**`Ref` rarely gives you what you want on Connect resources.** On the email address `Ref` returns
the address itself; on a contact flow it returns the flow's *name*. The ARNs are `GetAtt`
attributes — `EmailAddressArn` and `ContactFlowArn`, in CDK `attr_email_address_arn` and
`attr_contact_flow_arn` — and an id is the last segment of its ARN. Read each resource's *Return
values* section in the CloudFormation reference before wiring it into an output, a placeholder or
an API call. Getting a name where you expected an ARN is a normal stumble here; the deploy error or
a wrong output value is your evidence.

**Flows, and the designer round trip.** A flow is a program for a contact, made of **blocks**.
This lesson's flow needs two that work on email: **Set working queue**, which chooses the queue
the contact will go to, and **Transfer to queue**, which puts the contact in that queue and ends
the flow. A queue must be set before Transfer to queue runs. Each block has branches — Set
working queue has **Success** and **Error**; Transfer to queue has **At capacity** and **Error**
— and every branch must lead somewhere, typically to a block that ends the contact. Flows are
drawn in the admin website's flow designer and saved as JSON in the Amazon Connect **flow
language**; the designer can **Export flow** to a file (on the **Save** menu) and import one.

`#flow-round-trip` makes the file the source of truth. You draw the flow in the designer, export
it, and commit it as `flows/inbound-email.json`. The exported JSON contains the ARNs of the
things you picked in the designer — the queue, here — and those ARNs belong to one instance in
one account. So before you commit, you replace every one of them with a **placeholder** in
CloudFormation's `${Name}` form, for example `${BasicQueueArn}`. The routing stack reads the file
and passes it through `Fn.sub` with a map from each placeholder name to the real value, and
gives the result to `CfnContactFlow` (`AWS::Connect::ContactFlow`) as its `Content`. An inbound
email flow is an ordinary inbound flow: `Type` `CONTACT_FLOW`. `Fn.sub` treats every `${...}` in
the string as a substitution, so a placeholder you forgot to put in the map fails the deploy —
which is the behaviour you want.

**The console is where a flow is drawn; the file is what it is.** Once the flow is deployed from
the file, an edit made to it in the console is not in the file. CloudFormation updates a resource
only when its template changes, so the console edit survives — until the next deploy that
changes that flow, which overwrites it without a word, perhaps days later. That delay is what
makes it dangerous. The rule follows: every change is made in the designer *and exported*, or it
did not happen.

**The association.** Neither the email address nor the flow names the other. The link is made
by the `AssociateFlow` API with `ResourceType` `INBOUND_EMAIL`, the email address as
`ResourceId`, and the flow's id as `FlowId`; it is undone by `DisassociateFlow`. There is no
CloudFormation resource for it, so you make it with CDK's `AwsCustomResource` (from
`aws_cdk.custom_resources`): one SDK call on create and update, the opposite call on delete, and
an IAM policy that allows exactly those calls. It lives in `ConnectRouting` (`#stack-split`)
because it joins a long-lived thing (the address) to a churning thing (the flow), and only the
churning stack may know about both. An address with no flow associated receives mail into a
contact that has nowhere to go.

**The routing profile has to say "email".** A routing profile has two separate places where a
channel appears. Its **channel settings** list which channels its agents handle and how many
contacts of each at once. Its **queues** list each queue *with a channel*. A contact is offered
to an agent only if the agent's routing profile works the contact's queue on the contact's
channel, and has that channel enabled. AWS's own wording: a queue's channel must also be in the
channel settings, "If it isn't, contacts from that channel won't be routed to agents." Your agent
is still on the instance's default **Basic Routing Profile**. Which channels it includes, and on
which channels it works **BasicQueue**, is something you check on your own instance — not
something this lesson tells you.

**Replies and the SES sandbox.** The agent's reply leaves through Amazon SES. A new AWS account's
SES is in the **sandbox**, separately in each region: it can send only to verified addresses
(and to the SES mailbox simulator), at most 200 messages in 24 hours and one per second. AWS's
email setup guide for Connect tells you to request production access before you use email. For
this course you need not: if your SES is still in the sandbox in your region, verify your own
mailbox's address in SES and replies to it should be delivered. That last step is an inference
from how SES works, not something the Connect documentation states for this case; if a reply
does not arrive, the sandbox is the first suspect. When an agent replies, the From address
defaults to the address the customer wrote to.

## Concepts to teach

The contact as Connect's unit of work, and an email becoming a contact with the channel
`EMAIL`; email as an asynchronous channel, and the 14-day default lifetime of an active email
contact; the split between the console-only part of enabling email (service role, default
domain) and the coded part (two `InstanceStorageConfig`s); checking for storage configurations
the console may already have made, instead of assuming; the CORS requirement on the attachments
bucket; the message bucket as a store of personal data; `CfnEmailAddress`, the
`<alias>.email.connect.aws` domain, and that the resource names no flow; the flow designer,
blocks and branches, **Set working queue** and **Transfer to queue**; the flow language and
**Export flow**; `#flow-round-trip` — placeholders in `${Name}` form, `Fn.sub`, `CfnContactFlow`
with `Type` `CONTACT_FLOW`; why a console edit to a deployed flow is lost on the next deploy that
touches it; `AssociateFlow` with `INBOUND_EMAIL`, made as an `AwsCustomResource` with a matching
delete and a least-privilege policy, in the churning stack; the two places a routing profile
names a channel, and that a missing channel means a contact that waits unoffered; accepting and
replying in the agent's panel; the SES sandbox, per region, and verified addresses.

## Constraints

- You write every construct, the flow drawing, the placeholder edits and the tests yourself.
- The console step is limited to **Create service role** and **Add domain** with the Amazon
  Connect email domain. Storage configurations are code, not console settings.
- `ConnectCore` gains: the S3 bucket for messages and attachments, the two
  `CfnInstanceStorageConfig`s, and the `CfnEmailAddress` for `support@<alias>.email.connect.aws`.
  It publishes `EmailAddress` (the full address) and `EmailAddressId` (the address's id or ARN)
  as `CfnOutput`s with exactly those ids. It still refers to nothing in `ConnectRouting`.
- The bucket blocks public access and is encrypted. You decide its removal policy and its
  lifecycle, knowing it holds personal data, and you record the decision.
- `ConnectRouting` gains: the `CfnContactFlow` loaded from `flows/inbound-email.json` through
  `Fn.sub`, the `AwsCustomResource` that associates it with the address (and disassociates on
  delete), and a `CfnOutput` `InboundEmailFlowId` with the flow's id.
- `flows/inbound-email.json` contains no ARN, account id or region. Every resource reference is a
  `${Name}` placeholder.
- The flow for this lesson is minimal: set the working queue to BasicQueue and transfer to it,
  with every branch ending somewhere. Routing decisions are lessons
  `02-hours-queues-routing-profiles` and `03-flow-logic-for-email`.
- The custom resource's IAM policy allows the association calls it makes and nothing broader.
- You send the test email from your own mailbox, to your own instance. You do not send to, or
  put into the instance, anybody else's address.

## Suggested progression

Do the console step first, because the address cannot exist without the domain. In the Connect
console, open your instance's **Email** page, choose **Create service role**, then **Add domain**
with the Amazon Connect email domain. Read back the domain it shows you and confirm it is
`<alias>.email.connect.aws` for your alias. Stop there: do not visit **Data storage**.

Now check what the console left behind. List the instance's storage configurations for each of
the two resource types with `aws connect list-instance-storage-configs`, passing your instance id
and `--resource-type EMAIL_MESSAGES`, then `ATTACHMENTS`. If either already exists, you have a
decision to make before you write code — whether to remove it so that code owns it, or to leave
it and not declare it — and you discuss it with the tutor and record it. Do not guess what a
second configuration of the same type would do.

Write the bucket and the two storage configurations in `CoreStack`. Decide one bucket or two,
the prefixes, the encryption, the CORS rule the attachments bucket needs, and what happens to the
bucket's contents at teardown. Write the `CfnEmailAddress` and its two outputs. Deploy
`ConnectCore`. If the address or a storage configuration fails to create, read the
CloudFormation event message before you change anything; it is the first evidence you have.

Draw the flow. In the admin website, open the flow designer and create an inbound flow with a
name that is clearly a scratch copy. Add **Set working queue** set to **BasicQueue**, then
**Transfer to queue**, and send every error and at-capacity branch to a block that ends the
contact. Save it, then use **Export flow** and save the file into `flows/` as
`inbound-email.json`.

Open the file. Search it for `arn:` and look at every hit, including any outside the block
parameters. Replace each ARN with a placeholder — the queue becomes something like
`${BasicQueueArn}` — and keep a note of each name. The BasicQueue ARN is another looked-up value
you do not own; you know from lesson `00-instance-and-first-agent` what to call that, and lesson
`02-hours-queues-routing-profiles` removes it. Write a test that reads `flows/inbound-email.json`
and fails if it contains an ARN.

Write the `CfnContactFlow` in `RoutingStack`: read the file, pass it through `Fn.sub` with the
map, and give it a name different from your scratch copy. Add the `InboundEmailFlowId` output, and
check after deploying that its value really is an id and not the flow's name.
Now stop, and predict: deploy only this, send an email to your address, and what happens? Deploy
`ConnectRouting`, send a short email from your own mailbox to `support@<alias>.email.connect.aws`,
and wait a few minutes with your agent Available. Then look for the contact in the admin
website's contact search — through your emergency-access login, because the agent's security
profile cannot search contacts — and tell the tutor what you found. This is the first instructive
failure: an address and a flow that both exist, and nothing joining them.

Write the association as an `AwsCustomResource` in `RoutingStack`: `AssociateFlow` with
`INBOUND_EMAIL` on create and update, `DisassociateFlow` on delete, and a policy limited to those
calls. The API reference does not say whether `ResourceId` wants the address's id or its ARN for
an email address; find out from the API's behaviour and record what you learned. Deploy
`ConnectRouting`.

Before you send again, check your routing profile, because nobody else will. Find the Basic
Routing Profile's channel settings and its queues with their channels — in the admin website, or
with `aws connect describe-routing-profile` and `aws connect list-routing-profile-queues`. Does
it enable email? Does it work BasicQueue on the email channel? If it does not, your email will
wait in BasicQueue and never be offered to you: that is the second instructive failure, and you
can see it happen by sending an email now. The repair belongs in code, but you do not own a
routing profile until lesson `02-hours-queues-routing-profiles`; discuss with the tutor whether to
change the default profile by hand as recorded, temporary state, or to bring the course's own
routing profile forward. Either way, write down what you did.

Check SES before you reply. Read your account's SES status in your instance's region with
`aws sesv2 get-account` and look at `ProductionAccessEnabled`. If it is `false`, you are in the
sandbox: verify your own mailbox's address as an SES identity in that region, and confirm the
verification from your mailbox.

Send the email again. Accept the contact in the CCP, read it, and reply. Confirm the reply
reaches your mailbox.

Finally, meet the third instructive failure on purpose. Open your **deployed** flow — not the
scratch copy — in the designer, make a small visible change, such as the name of a block, and
publish it. Deploy `ConnectRouting` without changing the file, and look at the flow: is your edit
still there? Now make any small change to `flows/inbound-email.json`, deploy again, and look a
second time. Explain to the tutor what happened, and why the first deploy did not remove your
edit and the second did. Leave the deployed flow equal to the file, and delete the scratch copy
when you no longer need it.

## Completion conditions

- `ConnectCore` declares the message bucket, two `AWS::Connect::InstanceStorageConfig`s with
  `ResourceType` `EMAIL_MESSAGES` and `ATTACHMENTS`, and the `AWS::Connect::EmailAddress` for
  `support@<alias>.email.connect.aws`, and publishes `EmailAddress` and `EmailAddressId`.
- `ConnectRouting` declares the inbound flow, loaded from `flows/inbound-email.json` through
  `Fn.sub`, the `AwsCustomResource` that associates it with the address and disassociates it on
  delete, and the output `InboundEmailFlowId`. `ConnectCore` still refers to nothing in
  `ConnectRouting`.
- `flows/inbound-email.json` contains no ARN, and a test in `tests/` fails if it ever does.
- The `cdk-synth` and `pytest` validators pass.
- The `email-routed` validator passes. It reads your deployed address, the flow associated with
  it, and the most recent email contact back from your AWS account, so **send the test email and
  accept it before the tutor runs the check**. An address with no associated flow, or a contact
  that was never offered to your agent, does not pass.
- The reply you sent from the CCP has reached your mailbox, and you say so to the tutor.
- You can explain, without notes: what would have happened to an email if the association were
  missing; the two places a routing profile must name the email channel; why the association
  lives in `ConnectRouting`; and why a console edit to a deployed flow survived one deploy and not
  the next.

## On completion, persist

Record in the instance's `DESIGN.md`:

- that email was enabled with the console step (service role, default domain), on which date, and
  that the storage configurations are code;
- what the storage-configuration check found, and the decision taken;
- the bucket design: one or two buckets, prefixes, encryption, CORS, removal policy and
  lifecycle, and that it holds personal data;
- the placeholder names used in `flows/inbound-email.json` and what each maps to;
- whether `AssociateFlow` took the address's id or its ARN as `ResourceId`.

Record in `STATE.md`:

- the email address and that one email was routed, accepted and answered;
- the SES status in the region, and whether the learner's address is a verified identity;
- any hand change to the Basic Routing Profile, as **known intentional state** to be replaced in
  lesson `02-hours-queues-routing-profiles`;
- that the BasicQueue ARN is a looked-up value, to be removed in lesson
  `02-hours-queues-routing-profiles`;
- that the learner's own email address now exists in the instance's contact records and in the
  message bucket, to be removed at teardown.

## Optional deeper paths

- Open the stored message in the S3 bucket and compare what Connect keeps with what you sent.
- Read the exported flow JSON block by block against the flow language reference, and find what
  the designer stores that the flow does not need to run.
- Write a test that checks every `${Name}` in `flows/inbound-email.json` has a matching key in the
  map the stack passes to `Fn.sub`, so a renamed placeholder fails in seconds instead of at deploy.
- Read about requesting SES production access — the *ses sandbox* topic of the course's coverage —
  and what an account needs to show to be granted it.
- Look at what a custom email domain verified in SES would change, and why the course stays on
  `email.connect.aws` (`DESIGN.md`, *Deliberately unresolved*).
