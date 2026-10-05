---
id: 02-hours-queues-routing-profiles
title: Hours, queues and routing profiles
design_refs: [flow-round-trip]
validators: [cdk-synth, pytest, email-routed]
---

## Purpose

Route email on purpose — into the course's own queue, through its own hours and routing profile — instead of into the instance's defaults.

In lesson `01-first-email-contact` an email reached you because the instance's defaults happened
to line up: BasicQueue, the Basic Routing Profile, and two ARNs you looked up and hard-coded. None
of that is yours, none of it is tested, and none of it says *why* a contact went where it went.
This lesson replaces the defaults with resources your stack owns — **hours of operation**, a
**queue**, a **routing profile** — moves your agent onto them, and gives the flow its first real
decision: is the contact centre open? At the end, an email during hours and an email outside them
take different branches, the contact says which in its `route_reason` attribute, and you can show
both on demand without waiting for the clock.

## Prerequisites

Lesson `01-first-email-contact` complete: the email address `support@<alias>.email.connect.aws` in
`ConnectCore`; `flows/inbound-email.json` deployed from `ConnectRouting` with placeholders and
associated with the address; one email routed, accepted and answered. Your agent is still on the
Basic Routing Profile, whose ARN is a hard-coded constant in `RoutingStack` from lesson
`00-instance-and-first-agent`, and the flow still targets BasicQueue through a looked-up ARN.
`STATE.md` records any hand change you made to the default routing profile in lesson
`01-first-email-contact`.

## Learning objectives

- Explain how **hours of operation**, a **queue**, a **routing profile** and an **agent** compose
  into "who is offered this contact, and when"
- Declare `CfnHoursOfOperation`, `CfnQueue` and `CfnRoutingProfile` in `ConnectRouting`, and move
  the agent user onto the routing profile
- Configure a routing profile's **media concurrency** and **queue configuration** so that it offers
  email from the course queue, and explain why each of the two is needed
- Explain what a queue's hours do and do not do: they do not stop contacts arriving; a flow reads
  them and branches
- Add **Check hours of operation** to the flow with an out-of-hours branch, and decide what an
  out-of-hours email should get, given that email is asynchronous
- Set the contact attribute `route_reason` to `default` or `out-of-hours`, so the decision is
  visible on the contact
- Test out-of-hours by changing the hours, not by waiting

## Theory

**How the four pieces compose.** A contact centre answers two questions about every contact: *who
may handle it*, and *is now a time we handle it at all*. Connect splits the answer across four
resources:

- **Hours of operation** are a weekly schedule in a time zone: the times the business considers
  itself open. They are a resource of their own, so several queues can share one schedule.
- A **queue** is a waiting area for contacts. Every queue has hours of operation — the
  CloudFormation resource requires them — and optionally a limit on how many contacts may wait.
- A **routing profile** joins queues to agents. It lists queues, each on one or more channels, with
  a priority and a delay, and it lists the channels its agents handle and how many contacts of each
  they may have at once.
- An **agent** has exactly one routing profile, and a status. Only an Available agent is offered
  anything.

The flow chooses the queue; the routing profile decides which agents work that queue on that
channel; the hours are something the flow can consult. Keep the last part in mind, because it is
where intuition is wrong.

**What hours do — and what they do not.** It is natural to assume that a queue's hours *close* the
queue, so that an email arriving at night is refused or held. They do not, in the way this course
uses them. The **Transfer to queue** block's documented failures are a full queue (**At capacity**)
and an invalid or disabled queue (**Error**); closed hours are not among them. Hours act through the
**Check hours of operation** block: it compares now with a schedule and takes the **In hours** or
**Out of hours** branch (or **Error**). If you specify hours on the block, it checks those; if you do
not, it checks the hours of the contact's current working queue — so in that case **Set working
queue** must run first. A flow that never checks the hours routes the same way at 3 a.m. as at
3 p.m. You will prove this to yourself before you add the check.

**Out of hours means something different for email.** For a call, "closed" usually means a message
and a hang-up: nobody can hold a caller all night. An email is not waiting on a line. An active email
contact stays open — in a queue or with an agent — for 14 days by default, extendable to 90, before
it expires. So "out of hours" for email is a policy choice, not a necessity: you can queue it anyway
and let the morning shift find it; you can acknowledge it — "we have your message and will answer
when we open" — and then queue it; or you can send it to a different queue. All are legitimate. The
automatic acknowledgement uses the **Send message** block, which lesson `03-flow-logic-for-email`
teaches; in this lesson the decision is what to do and how to record it.

**The routing profile names a channel twice.** `AWS::Connect::RoutingProfile` (`CfnRoutingProfile`)
requires a `Name`, a `Description`, the `InstanceArn`, a `DefaultOutboundQueueArn` (the queue whose
settings an agent's own outbound contacts use) and `MediaConcurrencies`. Each **media concurrency**
names a `Channel` — `VOICE`, `CHAT`, `TASK` or `EMAIL` — and a `Concurrency`, how many contacts of
that channel an agent may have at once (voice is always exactly 1; email up to 10). Each **queue
config** in `QueueConfigs` has a `QueueReference` with the queue's ARN and a channel, a `Priority`
(1 is highest) and a `Delay` in seconds. The two lists are independent, and both must name email: a
queue configured for the email channel in a profile that has no email concurrency routes no email
to anybody, and so does a profile with email concurrency whose queue config names the queue only on
another channel. The contact waits. Nothing errors. Priority, delay and cross-channel behaviour
matter once there are two queues and two channels; they are lessons `03-flow-logic-for-email` and
`08-one-agent-two-channels`, and here you need only one queue on one channel.

**Owning the resources removes two smells.** Once your stack creates the routing profile, the
user's `RoutingProfileArn` comes from it, and the hard-coded Basic Routing Profile ARN from lesson
`00-instance-and-first-agent` disappears. Once the stack creates the queue, the flow's
`${BasicQueueArn}` placeholder becomes `${CourseQueueArn}`, filled from your own queue, and the
looked-up BasicQueue ARN disappears too. The hours, if the flow names them directly, become
`${HoursArn}`. Every placeholder is now filled from something the same stack declares, so a test can
check the whole chain. The Agent security profile stays looked up: you do not create security
profiles in this course, and that constant is recorded as such.

**`Ref` is not an ARN here.** The CloudFormation reference documents that `Ref` on a queue and on a
routing profile returns the resource's *name*, and that the ARN is a `GetAtt` attribute:
`QueueArn`, `RoutingProfileArn` and `HoursOfOperationArn`, which CDK exposes as
`attr_queue_arn`, `attr_routing_profile_arn` and `attr_hours_of_operation_arn`. A name where an
ARN belongs synthesizes happily and fails at deploy, or substitutes a name into the flow. If you
reach for `Ref` first and get a name, that is a fair stumble: read the deploy error, then the
resource's *Return values* section, and keep the habit of checking it for every Connect resource.
An id, where one is needed (`CourseQueueId`), is the last segment of the ARN.

**Hours in code.** `AWS::Connect::HoursOfOperation` (`CfnHoursOfOperation`) requires the
`InstanceArn`, a `Name`, a `TimeZone` and a `Config`: a list of entries, each with a `Day` (such as
`MONDAY`) and a `StartTime` and `EndTime`, each with `Hours` and `Minutes`. A day with no entry is
closed. Connect applies daylight saving time itself for time zones that observe it. Pick the time
zone that matches the hours you mean, and confirm in the admin website that the value you chose is
one Connect accepts. `HoursOfOperationOverrides` exist for holidays and exceptions; this lesson does
not need them.

**Testing out-of-hours without waiting.** Hours are configuration, and configuration is code. To
test the out-of-hours branch at 2 p.m., you do not wait until night: you change the schedule so
that now is outside it, deploy `ConnectRouting`, send an email, and put the schedule back. A test
you can run on demand, in both directions, is a test; one you can only run at night is an anecdote.

**Recording the decision on the contact.** The flow's **Set contact attributes** block stores a
key and value on the contact — a *user-defined* attribute — and works on email. Set on the
**current contact**, an attribute is visible in the contact record, to later flows and to Lambda.
The course's convention is the attribute `route_reason`, a short string saying why the queue was
chosen: here `default` for an email in hours and `out-of-hours` for one outside them. Later lessons
add values. Without it, the only evidence of which branch ran is your memory of the flow; lesson
`05-following-a-contact` is about why that is not evidence.

## Concepts to teach

Hours of operation as a weekly schedule in a time zone, shared by queues; the queue as a waiting
area that must have hours; the routing profile as the join between queues and agents; one routing
profile per agent; that hours do not stop contacts arriving and act only when a flow checks them;
**Check hours of operation**, its branches, and where it takes its hours from; email's 14-day
active lifetime and why "closed" is a policy for email rather than a necessity; the routing
profile's media concurrencies and queue configs as two independent places a channel must appear;
`DefaultOutboundQueueArn` as a required property; priority and delay named and deferred to lessons
`03-flow-logic-for-email` and `08-one-agent-two-channels`; replacing looked-up ARNs with resources
the stack owns, and the `${CourseQueueArn}` and `${HoursArn}` placeholders; `attr_*` versus `Ref`
for these resources; testing out-of-hours by changing the schedule and redeploying; the
`route_reason` contact attribute with the values `default` and `out-of-hours`, set with **Set
contact attributes** on the current contact.

## Constraints

- You write every construct, the flow changes and the tests yourself.
- The hours, the queue and the routing profile live in `ConnectRouting`. `ConnectCore` does not
  change in this lesson.
- `ConnectRouting` publishes a `CfnOutput` `CourseQueueId` with the course queue's id. Do not add
  `PriorityQueueId`; the priority queue arrives in lesson `03-flow-logic-for-email`.
- The routing profile offers email from the course queue: it has an `EMAIL` media concurrency and a
  queue config for the course queue on the `EMAIL` channel. You choose the concurrency and record
  why.
- The agent user's `RoutingProfileArn` comes from your routing profile. The hard-coded Basic
  Routing Profile ARN is gone from the code. Any hand change you made to the default profile in
  lesson `01-first-email-contact` is undone.
- The flow targets the course queue through `${CourseQueueArn}`. No BasicQueue ARN remains in the
  code or in `flows/inbound-email.json`, and the file still contains no ARN at all.
- The flow checks the hours and sets `route_reason` to `out-of-hours` on the out-of-hours branch
  and `default` on the in-hours branch, on the current contact, before the contact is transferred.
- Every branch of every block leads somewhere.
- The flow change is made in the designer, exported, and placeholdered again (`#flow-round-trip`).
  The deployed flow is never edited in the console without exporting.
- Out-of-hours is tested by changing the hours in code and deploying, never by waiting, and the
  hours are put back afterwards.

## Suggested progression

Start with the queue's hours, the queue and the routing profile, and nothing in the flow yet.
Write `CfnHoursOfOperation` with a schedule that is open now, and say what time zone it is in.
Write `CfnQueue` for the course queue with those hours. Write `CfnRoutingProfile` with the course
queue as its default outbound queue, and with media concurrencies and queue configs as you judge
they should be. Move your user onto it, and delete the Basic Routing Profile constant. If you
changed the default profile by hand in lesson `01-first-email-contact`, put it back. Add the
`CourseQueueId` output.

Change the flow's target. The designer works on real ARNs, not placeholders, so draw the change on
a scratch flow that holds real values: your scratch copy from lesson `01-first-email-contact` if you
kept it, or the deployed flow opened as a copy. Whether the designer will import a file that still
carries `${...}` placeholders is something to find out, not assume. Set the working queue to your new
course queue, export, and replace the ARN with `${CourseQueueArn}`. Update the `Fn.sub` map so
it fills the placeholder from your queue, and remove the BasicQueue entry. Extend your tests: the
routing profile has an email concurrency and a queue config for the course queue on the email
channel, and the user's routing profile is the one the stack declares. Deploy `ConnectRouting`, go
Available, send an email, and accept it. This proves the new chain before you add a decision to it.

Now make the instructive routing-profile failure real. Remove email from one of the two places it
must appear in the routing profile — your choice which — deploy, and send an email with your agent
Available. Predict before you look: is the email lost, refused, or something else? Find the contact
and say where it is and why you were not offered it. Then put the routing profile right, deploy, and
watch the waiting email be offered to you. Do it once more with the *other* place, if you have the
time; the two look identical from the agent's side, which is the lesson.

Next, the hours. Before you add any check to the flow, predict: if you change the course hours so
that now is *closed*, and send an email, what happens? Change the schedule in code so that the
current time falls outside it, deploy, send an email, and see what the agent is offered. Explain to
the tutor what you observed and what it says about what hours do on their own.

Add the decision. Decide first, and say it to the tutor: what should an email that arrives out of
hours get? Queue it as normal and record that it came in closed; or acknowledge it and queue it; or
send it somewhere else. Remember that email waits for days and a caller does not. If you choose an
acknowledgement, know that **Send message** is taught in lesson `03-flow-logic-for-email`; it is
fine to record the intent now and build it there. In the designer, add **Check hours of operation**
— decide whether it checks the working queue's hours (and therefore comes after **Set working
queue**) or names the hours itself through a `${HoursArn}` placeholder — and on each branch a **Set
contact attributes** that sets `route_reason` on the current contact: `out-of-hours` on the
out-of-hours branch, `default` in hours. Lead the **Error** branch somewhere you can recognise.
Export, placeholder every ARN, update the map, extend your tests, and deploy.

Demonstrate both ways on demand. With the hours still closed, send an email, accept it, and find
`route_reason` on the contact in its record, through contact search in the admin website (your
emergency-access login, not the agent's). Then change the schedule back so that now is open, deploy, send another email, and
find `route_reason` again. Each time, tell the tutor what you expect before you look. Leave the
hours set to the schedule you actually mean, and record it.

## Completion conditions

- `ConnectRouting` declares an `AWS::Connect::HoursOfOperation`, an `AWS::Connect::Queue` for the
  course queue using those hours, and an `AWS::Connect::RoutingProfile` with an `EMAIL` media
  concurrency and a queue config for the course queue on the `EMAIL` channel, and publishes
  `CourseQueueId`.
- The agent user's routing profile is the stack's own; no Basic Routing Profile ARN and no
  BasicQueue ARN remain in the code; `flows/inbound-email.json` contains no ARN and uses
  `${CourseQueueArn}` (and `${HoursArn}` if the block names the hours).
- The flow contains **Check hours of operation**, and its two branches set `route_reason` to
  `default` and `out-of-hours` on the current contact before transferring.
- The `cdk-synth` and `pytest` validators pass, with tests that assert the routing profile's email
  concurrency and queue config and the user's routing profile.
- The `email-routed` validator passes for an email sent during hours: the contact reached the
  course queue, was accepted by your agent, and carries `route_reason` `default`. **Send and accept
  the email before the tutor runs the check.**
- The `email-routed` validator also passes for an email sent while the hours were changed to closed:
  the contact carries `route_reason` `out-of-hours` and was handled as you decided. The tutor runs
  the check after each of the two test emails, so the two states are shown one after the other, on
  demand.
- You can explain, without notes: what a queue's hours do when no flow checks them; why a routing
  profile must name email in two places and what the agent sees when one is missing; what you
  decided an out-of-hours email should get and why that is different from a call; and how you
  tested out-of-hours without waiting.

## On completion, persist

Record in the instance's `DESIGN.md`:

- the hours of operation: the schedule, the time zone, and that it is the course's single schedule
  for now;
- the course queue and the routing profile, the email concurrency chosen and the reason;
- the **out-of-hours policy** for email — queue, acknowledge and queue, or another queue — and the
  reason, since lesson `03-flow-logic-for-email` may build on it and lesson `06-a-phone-line` has to
  decide the same thing for voice;
- whether **Check hours of operation** reads the working queue's hours or names them;
- the `route_reason` values the flow now sets: `default`, `out-of-hours`;
- the placeholders now in `flows/inbound-email.json` and what fills each.

Record in `STATE.md`:

- that the agent is on the course's own routing profile, and the hard-coded routing-profile and
  BasicQueue ARNs are gone; the Agent security profile ARN remains looked up, as intentional state;
- that both the in-hours and out-of-hours paths were demonstrated, with the contact ids if the
  learner kept them;
- that the hours were restored to the intended schedule after testing;
- any acknowledgement deferred to lesson `03-flow-logic-for-email`.

## Optional deeper paths

- Use `HoursOfOperationOverrides` to model a public holiday, and add the optional override branch to
  **Check hours of operation** so the holiday gets its own path.
- Read AWS's queue priority and delay examples and predict what a second queue at priority 2 with a
  30-second delay would do; lesson `08-one-agent-two-channels` makes this real.
- Change the contact's expiry for out-of-hours emails with the `connect:ContactExpiry` segment
  attribute, and decide whether 14 days is right for your policy.
- Set `MaxContacts` on the queue to a small number, fill it, and watch the **At capacity** branch of
  **Transfer to queue** — then decide what a full email queue should do.
- Look at the queue's outbound email configuration and decide which address your agent's own new
  emails should come from; replies already default to the address the customer wrote to.
