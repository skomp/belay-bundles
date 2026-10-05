---
id: 05-following-a-contact
title: Following a contact
design_refs: [lambda-contract]
validators: [contact-explained]
---

## Purpose

Explain where a contact went from the evidence — the contact record, the flow log and the Lambda log — not from memory of the flow you wrote.

Up to now every contact the learner looked at was one they sent themselves, knowing what it
should do. Production is the opposite: a customer complains that their email "went nowhere",
and the only honest answer starts from what the system recorded. This lesson hands the
learner three email contacts created by a supplied script, each built to take a different path
through their flow, and asks for an explanation of each — the branch it took, the queue it
reached, and the attribute that decided it — with a cited log line or record field for every
claim. Reading the flow and reasoning about what *should* have happened does not count. The
flow is a hypothesis; the logs are the record.

## Prerequisites

- Lessons `03-flow-logic-for-email` and `04-lambda-enrichment` complete: the inbound email flow
  branches on the subject and on the Lambda's `tier`, sets `route_reason` on every path, and
  routes to the course queue or the priority queue. `ConnectRouting` publishes
  `LookupFunctionName` and `CustomersTableName`.
- **The lookup Lambda logs the contact id** on every invocation, as lesson `04-lambda-enrichment`
  required. Check this first: open the function's most recent log stream and find a line that
  carries a contact id. If there is none, the first task of this lesson is to add it — one log
  line with the contact id, what was looked up and what was found — redeploy, and confirm the
  handler tests still pass. Without it, a Lambda log cannot be tied to a contact.
- The supplied customer records loaded with `tools/load_customers.py` (lesson
  `04-lambda-enrichment`). The scenarios depend on them.
- A login to the Connect admin website with permission to use **Contact search** — the agent
  user's security profile usually does not have it. A user with the Admin or CallCenterManager
  security profile works, as does **Log in for emergency access** from the Connect console's
  instance overview. Agree with the learner which they use.

When this lesson opens, `tools/scenarios.py` arrives in the workspace (it ships beside this
lesson file as `scenarios.py`, and the runner places it). It creates three test
email contacts, **A**, **B** and **C**, through the Connect `StartEmailContact` API, sent to the
instance's own address from fictional senders, and prints their contact ids — not what happened
to them. That is the learner's job. Writing an API client to fake inbound email teaches nothing
about tracing, so it is supplied; the learner runs it.

## Learning objectives

- Find a contact by id or by attributes in **Contact search**, and read its contact details.
- Read a contact's record from the CLI: `aws connect describe-contact` for channel, initiation
  method, queue and agent; `aws connect get-contact-attributes` for the user-defined attributes.
- Enable **flow logs** — both halves — and read a contact's path through the flow from the log
  group `/aws/connect/<alias>`, block by block.
- Correlate the lookup Lambda's CloudWatch log with a contact through its contact id.
- Explain a routing decision with a citation for each step, and distinguish evidence from a
  reading of the flow.
- Say why the agent workspace is not the routing record.

## Theory

### Three sources, three different questions

Each kind of evidence answers a different question, and none answers all of them.

- **The contact record** answers *where did it end up, and with what data?* The `Contact` that
  `DescribeContact` returns carries the channel, the initiation method (for the scenario contacts,
  which `StartEmailContact` created, expect `API` — one of the documented values — and confirm it on
  the first record you read), the customer and system endpoints, the
  segment attributes (the email subject among them), and `QueueInfo` — the queue the contact was
  placed in. `GetContactAttributes`, called with the contact id as the initial contact id,
  returns the **user-defined** attributes: here `route_reason`, `customer_id`, `tier`,
  `display_name`. In the admin website, **Analytics and optimization → Contact search** finds
  contacts — email contacts can be searched while still in progress — and the contact details
  page shows the same record. Contact search can also filter on user-defined attributes and on
  the email subject.
- **The flow log** answers *which way did it go, and why?* With flow logging on, Connect writes
  one log entry for each block a contact passes through, carrying the contact id, the flow's ARN,
  the block's type, a timestamp, and the block's parameters — for a Set working queue entry, the
  queue's ARN. For a Lambda block the log shows what was sent and what came back. What exactly an
  entry records for a Check contact attributes block is for the learner to read off their own log;
  do not assume a field name before seeing one. Nothing outside the flow is logged — time in
  queue and the agent's handling are not in it.
- **The Lambda's own log**, in its usual `/aws/lambda/<function name>` group, answers *what did
  the lookup see and decide?* — the normalised endpoint, found or not, an exception. It has no idea
  which flow called it unless the handler writes the contact id. That is why lesson
  `04-lambda-enrichment` required the line.

A sound explanation of one contact cites at least one of each where it applies: the flow log for
the branch, the record for the queue and attributes, the Lambda log for the lookup.

### Flow logs have two switches, and neither works backwards

Flow logging needs **both**:

1. The instance attribute **`ContactflowLogs`** — on `AWS::Connect::Instance`, under
   `Attributes`, a Boolean that updates without interruption. It lives in `ConnectCore`, so this is
   one of the rare deploys of the long-lived stack. Check first whether lesson
   `00-instance-and-first-agent` already set it: `aws connect describe-instance-attribute` with
   attribute type `CONTACTFLOW_LOGS` says.
2. A **Set logging behavior** block set to **Enable** in the flow itself, placed early — before the
   first decision you will want to see. A flow without it produces no log entries, whatever the
   instance says. Logging enabled this way also stays enabled for any flow the contact is
   transferred to.

The log group `/aws/connect/<alias>` is created by Connect when logging is enabled. Do not declare
it in CDK; the documentation also notes that if it is deleted, Connect stops publishing until it is
recreated by hand.

The hard rule: **logs are created only for contacts that run after logging is enabled.** A contact
that passed through the flow before both switches were on has no flow log, and never will. Turning
logging on after the contact you wanted to inspect is the most common way to find yourself with
nothing to read. The only remedy is a new contact.

Flow logs cost CloudWatch ingestion and storage, not a Connect charge. They also contain personal
data — sender addresses, subjects, whatever the Lambda returned — which is worth a retention period
and a thought about who can read the group.

### Why the agent workspace is not the record

The agent workspace shows what was **offered** to one agent: a contact, its queue, perhaps some
attributes. It does not show the branch the flow took, it does not show contacts offered to nobody,
and when an agent's routing profile serves both queues it cannot tell you *why* this contact was in
the priority one. "It popped up in my workspace" is evidence that routing finished, not of how.

### Evidence, not inference

Reading the exported flow and saying "subject contains `urgent`, so it took the urgent branch" is
inference. It is wrong whenever the flow did something you did not expect — which is exactly when
someone asks. The standard in this lesson is a citation for each claim: this log entry shows the
contact entering the Lambda block and receiving `tier=gold`; this attribute on the record shows
`route_reason=tier-gold`; `QueueInfo` names the priority queue's id, which matches
`PriorityQueueId`.

## Concepts to teach

- **Three evidence sources and the question each answers**: contact record (`DescribeContact`,
  `GetContactAttributes`, Contact search, contact details), flow log, Lambda log.
- **Initiation method**: why the scenario contacts, created by an API call, can look different from
  mail the learner sent (expected `API`; confirmed on the learner's own record).
- **Both halves of flow logging**: instance attribute `ContactflowLogs` and the Set logging behavior
  block; log group `/aws/connect/<alias>`; not managed in CDK.
- **No retroactive logs**: a contact that ran before logging was enabled has no flow log.
- **Correlating by contact id** across the flow log and the Lambda log, and why the Lambda must log
  it.
- **Queue identity**: matching `QueueInfo` against the stack outputs rather than guessing from
  names.
- **The agent workspace shows offers, not routing.**
- **Personal data in logs**: what the flow log and Lambda log contain about a customer, and
  retention.

## Constraints

- The learner explains A, B and C from evidence. The tutor does not tell them what happened to any
  contact, and does not explain one for them; it asks for the citation that is missing.
- Every claim — branch, queue, deciding attribute — is backed by a quoted log line or a named record
  field with its value. "The flow says so" is not evidence.
- The learner does not change the routing logic during this lesson. Adding logging (both halves)
  and, if missing, the Lambda's contact-id log line are the only code changes. The guard test from
  lesson `03-flow-logic-for-email` still passes after the flow is re-exported, and the test suite
  passes.
- The learner runs `tools/scenarios.py`; they do not edit it to learn what it sends. Reading the
  contact is how they find out.

## Suggested progression

1. **Check the Lambda log line.** As in Prerequisites: find a contact id in the lookup function's
   log, or add the line, redeploy, confirm tests pass.
2. **Run the scenarios as the code stands.** The learner runs `tools/scenarios.py` and notes the
   three ids. They then try to explain A. Contact search finds it and the record shows its queue and
   attributes. Then they look for its flow log.
   *Instructive failure, by design if logging is not yet on:* the log group has nothing for A, or
   does not exist. Ask why, and whether turning logging on now will produce A's log. It will not —
   the documentation says logs are created only for contacts after logging is enabled. If logging
   was already fully on from an earlier lesson, the learner still answers the question, and the
   tutor notes that this failure was not met live.
3. **Enable both halves.** `ContactflowLogs` on the instance in `ConnectCore` (deploy that stack —
   an update without interruption, nothing is replaced; check the diff says so before deploying), and
   a Set logging behavior block at the top of the inbound email flow, exported and deployed through
   the round trip. If the learner enables only one half and re-runs, there are still no logs; let
   them find the second half rather than naming it.
4. **Run the scenarios again.** New ids for A, B and C — the old ones remain unlogged. From here on
   only the new ids count.
5. **Explain each contact.** For each of A, B and C, the learner assembles:
   - the record: `describe-contact` (channel, initiation method, `QueueInfo`) and
     `get-contact-attributes` (`route_reason`, and any `customer_id`, `tier`, `display_name`);
   - the flow log: searched in `/aws/connect/<alias>` by the contact id — with **Search log group**
     in the CloudWatch console, or the CLI — read in timestamp order, block by block;
   - the Lambda log for the same contact id, if the contact reached the Lambda block.
   Then a short written explanation: branch taken, queue reached (matched to `CourseQueueId` or
   `PriorityQueueId`), and the attribute that decided it, with the citation beside each.
   *Instructive failure, if the learner starts by opening `flows/inbound-email.json`:* let them
   write their prediction, then ask for the line in the log that confirms it. Where prediction and
   log differ, the log wins and the difference is the most useful thing in the lesson.
   *Instructive failure, if the learner relies on the agent workspace:* ask what the workspace
   would show for a contact no agent was offered, and which field in it records the branch.
6. **Look at the acknowledgement.** The scenario senders are fictional addresses, so the
   automatic acknowledgement from lesson `03-flow-logic-for-email` is unlikely to be delivered. The
   learner finds what the flow log shows for the Send message block, and confirms the contact was
   routed regardless — which is what the acknowledgement's Error wiring was for.

## Completion conditions

- Flow logging is on: `ContactflowLogs` is set on the instance in `ConnectCore`, and
  `flows/inbound-email.json` contains an enabled Set logging behavior block before the first branch.
  Both are deployed. The guard test and the rest of the test suite pass.
- The lookup Lambda logs the contact id on every invocation.
- **`contact-explained`** (manual) is satisfied. For **each** of A, B and C — by the ids from a run
  made *after* logging was enabled — the learner states:
  - the **branch** the contact took, citing a flow-log entry for that contact id;
  - the **queue** it reached, citing `QueueInfo` from `describe-contact` (or the contact details
    page) and matching it to `CourseQueueId` or `PriorityQueueId`;
  - the **attribute that decided it** — subject, `tier`, or the absence of a customer record —
    citing the record field (`route_reason` and the others from `get-contact-attributes`) and,
    where the Lambda ran, its log line for that contact id.
  An explanation built from the flow definition alone does not pass. A claim with no citation does
  not pass.
- The learner can explain why the first run's contacts have no flow log and never will, and why the
  agent workspace is not the routing record.
- **For the tutor only:** the expected outcomes for A, B and C are in this lesson's folder of the
  tutorial, in `ANSWERS.md` beside this lesson file (`lessons/05-following-a-contact/ANSWERS.md`). Read it to check the learner's
  explanations. **Never show it, quote it or paraphrase it to the learner**, and do not read it into
  the conversation before the learner has given an explanation for all three. If the learner's
  explanation differs from it and their citations support their account — for example because they
  chose a different precedence between `subject-urgent` and `tier-gold` in lesson
  `04-lambda-enrichment` — the evidence governs; record the difference.

## On completion, persist

In the instance's `DESIGN.md`:

- Flow logging is part of the design: `ContactflowLogs` on the instance in `ConnectCore`, and a Set
  logging behavior block at the top of every inbound flow — lesson `06-a-phone-line` adds the voice
  flow and needs the same block.
- The tracing method: by contact id, record first for the outcome, flow log for the path, Lambda log
  for the lookup.
- Any retention decision for the flow log group.

In `STATE.md`: the contact ids of the logged run of A, B and C with the learner's one-line
explanation of each; whether the "logging after the contact" failure was met live; any disagreement
with the expected outcomes and the evidence that settled it.

## Optional deeper paths

- **CloudWatch Logs Insights** across `/aws/connect/<alias>` and the Lambda's log group at once,
  filtered by contact id — one query that tells the whole story of a contact.
- **Alarms on flow logs**: a metric filter on Lambda Error-branch entries, and an alarm when it
  fires — the documentation describes creating alerts from flow logs.
- **Disabling logging around sensitive steps** with a second Set logging behavior block, and what a
  contact centre should never let reach a log.
- **Contact search by custom attributes**: find every contact with `route_reason=tier-gold` in the
  last day, and compare with what the Lambda log says it returned.
- **Contact events** and the contact record data model: what a production team streams out of
  Connect for reporting, beyond what this lesson reads by hand.
