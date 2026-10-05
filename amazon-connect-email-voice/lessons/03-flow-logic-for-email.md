---
id: 03-flow-logic-for-email
title: Flow logic for email
design_refs: [flow-round-trip]
validators: [cdk-synth, pytest, email-routed]
---

## Purpose

Make the inbound email flow decide something: read the contact's attributes, branch on them, acknowledge the customer automatically and send urgent mail to a second queue.

Until now every email in hours takes the same path into the course's own queue. A real
contact centre does not work that way. An email that says "urgent" in its subject should not
wait behind a newsletter reply, and the customer should hear back at once that their message
arrived. This lesson adds that logic to the flow: a **priority queue**, a branch on the
email's subject, an automatic acknowledgement, and a `route_reason` attribute on every
contact that records why it went where it went. That attribute is what makes lesson
`05-following-a-contact` possible — a routing decision you can read off the contact
afterwards instead of reconstructing from the flow.

## Prerequisites

- Lesson `01-first-email-contact`: the email address `support@<alias>.email.connect.aws`
  (output `EmailAddress`), `flows/inbound-email.json` deployed through `Fn.sub` from the
  `ConnectRouting` stack, associated with the address, and the round trip (draw in the
  designer, export, replace ARNs with `${...}` placeholders, deploy) already done once.
- Lesson `02-hours-queues-routing-profiles`: hours of operation, the course queue (output
  `CourseQueueId`, placeholder `${CourseQueueArn}`), the out-of-hours branch, and the agent
  on the course's own routing profile with the email channel enabled.
- The agent can log in to the agent workspace and go Available (lesson
  `00-instance-and-first-agent`).
- The test suite and `cdk synth` pass on the current code.

## Learning objectives

- Distinguish the kinds of **contact attribute** a flow can read — system attributes,
  segment attributes, user-defined attributes — and say which namespace the email subject
  lives in and which one a flow can write to.
- Branch a flow with **Check contact attributes**, including what the **No match** branch
  means and that the comparison is case-sensitive.
- Set the working queue per branch and record the reason with a user-defined attribute,
  `route_reason`, on every path through the flow.
- Send an **automatic acknowledgement** with the **Send message** block as plain text, with
  To and From set dynamically, and explain why it never belongs in an outbound flow.
- Add a second queue (`PriorityQueue`) to the churning stack and to the agent's routing
  profile, and reference it from the flow by placeholder only.
- Recognise three instructive failures: branching on an attribute that was never set, a
  voice-only block in an email flow, and a hard-coded ARN in the exported JSON.

## Theory

### A flow reads attributes, and attributes live in namespaces

A contact carries data as **contact attributes**: key–value pairs a flow can read, compare
and copy. They are not one flat bag. Connect sorts them into namespaces, and the designer
asks you for the namespace before it asks for the key:

- **System** attributes are set by Connect and only read by you: the contact's `Channel`
  (`VOICE`, `CHAT`, `TASK`, `EMAIL`), its contact id, the **Customer endpoint address** (for
  an email, the sender's address), the **System email address** (the address the customer
  wrote to), and the current queue.
- **Segment attributes** are system-defined values stored on one contact segment. For email
  this is where the subject lives: **Email Subject**, JSONPath
  `$.SegmentAttributes['connect:EmailSubject']`. Amazon SES's spam and virus verdicts for the
  incoming message are segment attributes too.
- **User-defined** attributes are yours: any key you choose (without `$` or `.`), written by
  a **Set contact attributes** block, read back as `$.Attributes.<key>`. They are stored on
  the contact record, which is why they are the right place for a routing decision you want
  to read later.

The AWS documentation for setting up email says it directly: in a **Check contact
attributes** block you can check the segment attribute **Email Subject** for keywords. So no
copying step is needed before the branch — the block reads the segment attribute where it is.
What the segment attribute does *not* do for you is record a decision. That is
`route_reason`'s job.

### Branching: Check contact attributes and the silent No match

**Check contact attributes** compares one attribute against conditions in order — **Equals**,
**Contains**, **Starts With**, **Is Greater Than** and others — and takes the first branch
that matches. If nothing matches, the contact leaves on **No match**. It supports the email
channel.

Two properties of this block shape this lesson:

- **No match is not an error.** If you point the block at an attribute that does not exist —
  a user-defined key nothing ever set, a typo in the key, the wrong namespace — the comparison
  simply fails, the contact takes No match, and nothing anywhere complains. The flow looks
  right in the designer and routes every contact the default way. This is the commonest bug in
  flow logic, and the only defence is evidence: a test email that should take the branch, and
  a `route_reason` that says whether it did.
- **Matching is case-sensitive.** The documentation states the block does not support
  case-insensitive matching: a condition for `urgent` does not match `URGENT` or `Urgent`.
  Your rule has to say what it does about that, deliberately.

### Setting the queue, and saying why

**Set working queue** chooses the queue a contact will wait in; **Transfer to queue** then
puts it there. You already do this for the course queue. Each branch now sets its own queue,
and each branch also runs a **Set contact attributes** block that writes `route_reason` — a
short string such as `subject-urgent`, `default` or `out-of-hours`. An attribute set on the
**Current contact** is stored on the contact and visible to other flows, Lambdas, the contact
record and the APIs. A **Flow**-scoped attribute is not; it vanishes with the flow, so it is
the wrong choice here.

A contact only reaches an agent through a queue that the agent's **routing profile** lists,
on a channel the routing profile enables. A new queue that is not in the routing profile is
a queue nobody is offered — the same failure lesson `02-hours-queues-routing-profiles`
showed, in a new place.

### Acknowledging the customer: Send message

The **Send message** block sends an email from inside the flow. Configured with plain text
(no template — templates need an Amazon Q in Connect knowledge base, which this course does
not build), it takes:

- **From**: an email address of your instance. Set it *dynamically* to System → **System
  email address**, which is the address the customer wrote to.
- **To**: set it dynamically to System → **Customer endpoint address**.
- **Subject** (up to 998 characters) and **Message** (plain text, up to 5000 characters). The
  subject can reuse the customer's own, via Segment attribute → **Email Subject**.
- **Link to contact**: whether the outbound email contact is linked to the inbound one. The
  documentation suggests you may not want this for an automatic acknowledgement.

Sending is itself a contact: Send message creates an **outbound email contact**, and that
contact runs the **Default outbound flow** unless told otherwise. That is why AWS warns
never to put a Send message block with the EMAIL type into the Default outbound flow, or any
outbound flow, without safeguards: each acknowledgement would start another outbound contact
that sends another acknowledgement — a mail loop. The acknowledgement belongs in the
**inbound** flow only.

Send message has an **Error** branch, taken for example when the From address does not exist
on the instance or the sending service fails. An acknowledgement that fails must not stop the
email being routed: wire its Error branch onward to the same routing as Success.

**Amazon SES sandbox.** Connect sends outbound email through Amazon SES. A new account's SES
starts in a sandbox that delivers only to verified addresses, at most 200 messages a day and
one a second. That this sandbox applies to Connect's own sending is the course's inference
from how Connect uses SES, not a statement in the Connect documentation. Your reply in lesson
`01-first-email-contact` already showed what your account does; expect the acknowledgement to
behave the same way, and expect it to fail for any address that is not verified.

### Not every block works on every channel

Every flow block's documentation page has a table of the channels it supports. Some blocks are
voice- or chat-only. **Play prompt** — the first block anyone reaches for to "greet the
customer" — is one: the documentation says an email contact routed to it takes the **Error**
branch. **Get customer input**, the menu block lesson `07-voice-menu-and-caller-lookup` uses,
lists Email as unsupported. A voice-only block in an email flow does not stop the deploy; it
fails per contact, at run time, down a branch you may not have wired.

### ARNs in the export

When you choose a queue or an email address from a dropdown in the designer, the export
records that resource's **ARN** — account id, region, instance id and resource id baked into
the JSON. `#flow-round-trip` requires every one of them to become a `${Name}` placeholder that
the stack fills with `Fn.sub`. A literal ARN deploys only into the account and instance it
came from, and breaks silently the day the queue it names is replaced. Choosing values
*dynamically* from attributes (as with the Send message addresses above) avoids the ARN
altogether; choosing them from a dropdown means a placeholder.

## Concepts to teach

- **Contact attribute namespaces**: system, segment, user-defined; which ones a flow may
  write; JSONPath forms `$.Channel`, `$.SegmentAttributes['connect:EmailSubject']`,
  `$.Attributes.<key>`.
- **Check contact attributes**: ordered conditions, first match wins, **No match** as the
  silent fallthrough for an unset or misnamed attribute, case-sensitive comparison.
- **Set working queue** per branch, with a matching **Set contact attributes** writing
  `route_reason` on the current contact, on every path including out-of-hours.
- **Current contact vs flow attributes**: only the first is stored on the contact record.
- **Send message for an automatic acknowledgement**: plain text, To and From set
  dynamically, Link to contact, its Error branch, and the outbound-flow mail loop.
- **SES sandbox** as the likely reason an acknowledgement to an unverified address fails
  (inferred, see Theory).
- **Channel support per block**: Play prompt takes Error on email; Get customer input does not
  support email.
- **A second queue is not reachable until the routing profile lists it** on the email channel.
- **Placeholders, not ARNs**, in `flows/inbound-email.json`, enforced by the guard test the
  learner wrote in lesson `01-first-email-contact`, and extended here so that every
  placeholder in the file has a value in the `Fn.sub` map and every map entry is used.

## Constraints

- The learner draws the flow in the designer, exports it, and edits the export into
  `flows/inbound-email.json` with placeholders. The tutor describes what the flow must do and
  checks the result; it does not write the flow JSON or the CDK code.
- The priority queue is a new queue construct in `ConnectRouting`, using the hours from lesson
  `02-hours-queues-routing-profiles`, published as the `CfnOutput` **`PriorityQueueId`** and
  referenced in the flow only as `${PriorityQueueArn}`.
- The agent's routing profile lists both queues on the email channel.
- Every path through the flow that reaches a queue sets the user-defined attribute
  `route_reason` on the current contact: `subject-urgent` for the urgent branch, `default` for
  the ordinary in-hours path, `out-of-hours` for the out-of-hours branch (or the learner's own
  equally explicit values, recorded in `DESIGN.md`).
- The acknowledgement uses **Send message** with plain text — no message template — in the
  inbound flow only. The Default outbound flow is not modified.
- The acknowledgement's Error branch continues to routing; a failed acknowledgement never
  strands the contact.
- `flows/inbound-email.json` contains no literal `arn:` string. The guard test the learner
  wrote in lesson `01-first-email-contact` asserts this; it is not written a second time. It is
  extended, before the export it guards, so that the set of `${Name}` placeholders in the file
  and the set of keys in the `Fn.sub` map are the same.
- No Lambda yet. Customer lookup is lesson `04-lambda-enrichment`.

## Suggested progression

Design on paper first, then in the stack, then in the designer.

1. **Decide the rule.** With the learner, write down the urgent rule in one sentence: which
   attribute, which operator, which value, and what happens to `Urgent` and `URGENT`. The
   block cannot match case-insensitively, so the learner either lists the variants they accept
   or decides that only one spelling counts — and records which. Write down the `route_reason`
   values for every path, including out-of-hours.
2. **Extend the guard test.** The learner already has a test from lesson
   `01-first-email-contact` that fails if `flows/inbound-email.json` contains an ARN. Run the
   suite first: it should pass on the current file. Then the learner adds the check that test
   does not make: every `${Name}` placeholder in the file is a key in the substitution map the
   stack passes to `Fn.sub`, **and** every key in the map appears in the file. Ask what each
   direction catches — a typo in a placeholder, otherwise found only at deploy; a map entry left
   behind after a block was removed. The learner decides how the test reads the map from the
   stack code without duplicating it, and makes the test fail once on purpose (for example by
   misspelling one placeholder in the file, then putting it back) to see that it can.
3. **Add the priority queue** in `ConnectRouting` with output `PriorityQueueId`, add it to the
   routing profile on the email channel, add `PriorityQueueArn` to the placeholder map. Extend
   the template tests: two queues, the routing profile lists both, the output exists. Deploy
   the routing stack; the flow is unchanged so far.
4. **Draw the branch** in the designer on the deployed flow: after the hours check, a Check
   contact attributes block on the subject; on the match, Set contact attributes
   (`route_reason`) and Set working queue (priority); on No match, the same pair for the
   default path. Make sure the out-of-hours path sets its `route_reason` too.
   *Instructive failure, let it happen if the learner reaches for it:* choosing the
   **User defined** namespace and a key like `EmailSubject` or `subject`. Nothing ever set that
   attribute, so every email takes No match. The test email in step 7 exposes it — the urgent
   email arrives with `route_reason=default`. Ask the learner what the attribute's value was
   when the block ran, and where it would have come from.
5. **Add the acknowledgement** with Send message: plain text, From = System email address, To
   = Customer endpoint address, a subject that can reuse the customer's, Link to contact
   decided and recorded. Wire both Success and Error onward to routing. Ask before they place
   it: which flow does the outbound email contact it creates run, and what would happen if this
   block were in that flow?
   *Instructive failure, if the learner wants a greeting:* a Play prompt block "to say thank
   you". Let them see what the block's channel table says, or let a test email take its Error
   branch, and ask what the email-capable equivalent is.
6. **Export and replace.** Export the flow, write it over `flows/inbound-email.json`, and run
   the tests before replacing anything.
   *Planned failure, and the point of step 2:* the export contains the priority queue's ARN
   (and, if the From address was chosen manually from the dropdown, the email address's). The
   lesson 01 guard test fails on it — the learner watches the test they already own catch the
   new ARN, and reads which line it names. The learner replaces each with its placeholder — or,
   for the From address, switches to the dynamic System email address. If a new placeholder is
   not yet in the `Fn.sub` map, the extended test from step 2 fails next. Continue until the
   suite passes and `cdk synth` succeeds. Deploy.
7. **Test both ways.** The learner sends two emails from their own mailbox during hours: one
   whose subject matches the rule, one that does not. In the agent workspace both are offered;
   the acknowledgement arrives in the mailbox (or demonstrably does not, and the learner says
   why). The tutor runs `email-routed` after each. Then the learner reads `route_reason` and the
   queue for each contact in the admin website's contact details or with the CLI, and confirms
   they differ in the way the rule predicts. Optionally, a third email with the keyword in a
   different case shows the case rule they chose actually holds.

## Completion conditions

- `cdk-synth` passes, and `pytest` passes with: the lesson 01 test asserting that
  `flows/inbound-email.json` contains no ARN; a test that the file's `${Name}` placeholders and
  the `Fn.sub` map's keys are the same set; template tests for a second queue, both
  queues in the routing profile on the email channel, and the `PriorityQueueId` output.
- `ConnectRouting` is deployed and publishes `PriorityQueueId`; the deployed flow is the one in
  `flows/inbound-email.json` (no console-only edits).
- Two test emails sent by the learner during hours: the one matching the urgent rule reached
  the priority queue with `route_reason=subject-urgent`; the other reached the course queue
  with `route_reason=default`. The tutor runs `email-routed` for each, and the learner shows
  the queue and `route_reason` of both contacts from the contact record, not from memory.
- The learner received the automatic acknowledgement in their own mailbox, or can name the
  evidence for why it was not delivered (for example the SES sandbox and an unverified
  address) and shows the contact was still routed.
- The out-of-hours path sets `route_reason` too; the learner points to it in the exported JSON.
- The learner can explain: why a branch on an attribute nothing set takes No match silently;
  why Send message must not sit in the Default outbound flow; what a Play prompt block does to
  an email contact; and why the export may not contain an ARN.

## On completion, persist

In the instance's `DESIGN.md`:

- The urgent rule exactly as implemented — attribute, operator, value, and the decision about
  letter case.
- The `route_reason` vocabulary in use (`subject-urgent`, `default`, `out-of-hours`, or the
  learner's values), as the course-wide record of why a contact went where it went. Lesson
  `04-lambda-enrichment` adds to it.
- The acknowledgement's design: Send message in the inbound flow only, plain text, From/To set
  dynamically, Link to contact choice, Error branch continues to routing.
- The placeholder map now includes `PriorityQueueArn`.

In `STATE.md`: the two test contacts' ids and which queue each reached; whether the
acknowledgement was delivered, and if not, why; any instructive failure the learner actually
hit.

## Optional deeper paths

- **Spam and virus verdicts.** The segment attributes for the SES spam and virus verdicts can
  be checked for `FAILED` before anything else, routing such mail to a review queue or ending
  it. Discuss where in the flow that check belongs and why.
- **Branching on the sender.** The course allows the rule to match the subject *or* the sender.
  A Check contact attributes on the Customer endpoint address with **Starts With** or
  **Contains** works for a domain rule — and shows why identifying *people* belongs in the
  Lambda of lesson `04-lambda-enrichment` instead of a growing list of conditions.
- **Compound conditions.** Newer instances allow **And**/**Or** conditions inside one branch;
  the documentation marks this as available only on some instances. Check whether yours offers
  it, and whether it makes the case-variants list shorter.
- **Message templates** with an Amazon Q in Connect knowledge base: what they add over plain
  text, and why this course leaves them out.
