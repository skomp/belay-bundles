---
id: 06-a-phone-line
title: A phone line
design_refs: [stack-split, instance-choices, flow-round-trip]
validators: [cdk-synth, pytest, call-routed]
---

## Purpose

Add voice as a second channel, on the hours, queue and routing profile that email already uses.

Up to now every contact has been an email. That made routing cheap to learn, because an email
waits in a queue while you read the console. A contact centre usually also has a phone line,
and adding one shows which parts of what you built belong to a channel and which parts are
shared. In this lesson you claim a US phone number in the long-lived stack, draw an inbound voice
flow, deploy it from `flows/`, associate it with the number, and give your agent's routing
profile a voice channel. At the end you ring the number from your own phone, hear your flow
speak, and your agent accepts the call in the agent workspace. The call goes through the same
hours check and into the same queue as your email. There is no menu and no caller lookup yet.
Those come in lesson `07-voice-menu-and-caller-lookup`.

## Prerequisites

- Lessons `00-instance-and-first-agent` to `05-following-a-contact` are complete. `ConnectCore`
  and `ConnectRouting` deploy. An email to `EmailAddress` reaches your agent through
  `flows/inbound-email.json`, the hours from lesson `02-hours-queues-routing-profiles`, the queue
  behind `CourseQueueId`, and the routing profile your agent uses.
- Flow logging is on: the instance attribute `ContactflowLogs` and a Set logging behavior block,
  from lesson `05-following-a-contact`. You will need both when a test call does something you
  did not expect.
- A phone that can call a US number. From outside the US each test call is an international
  call. Know what your plan charges before you start.
- A browser that can use a microphone for the agent workspace softphone.

## Learning objectives

- Claim a phone number with `CfnPhoneNumber` in `ConnectCore`, and explain why it belongs in the
  long-lived stack and what a replacement would do to it (`#stack-split`)
- Explain why the course's number is a US DID whatever region your instance is in, which
  regulatory problem that avoids, and what it costs you (`#instance-choices`)
- Name what a claimed number costs while it exists, and where the course says how to stop that
  cost
- Draw an inbound voice flow (a text-to-speech prompt, the hours check, the working queue, the
  transfer), export it, and deploy it from `flows/inbound-voice.json` with placeholders in place
  of every ARN (`#flow-round-trip`)
- Connect the number to the flow with an `AwsCustomResource` in `ConnectRouting` that associates
  on create and update and disassociates on delete
- Explain which flow blocks the email flow cannot share with voice, and why the voice flow is a
  separate file
- Add voice to the agent's routing profile: a `VOICE` media concurrency and a `VOICE` queue
  configuration for the course queue, and explain why voice concurrency is always 1

## Theory

**A phone number is a resource you rent, not a resource you describe.** Most of what you have
built is configuration. If CloudFormation deletes a queue and creates it again, you get the same
queue with a new ARN. A phone number is not like that. `AWS::Connect::PhoneNumber` claims a
real number from the telephone network to your instance (its `TargetArn`). The Amazon Connect
documentation states that a released number cannot be claimed back, and that another customer
may claim it later. The number you print in a README and save in your phone is gone. A
number released through the `ReleasePhoneNumber` API also enters a cool-down of up to 180 days.
Connect also limits how often an account can claim and release numbers. The default is 200% of
the account's quota for active numbers in a rolling 180 days. An account that exceeds it cannot
claim numbers until the period ends. So it matters which properties of the resource force a
replacement. In the CloudFormation reference, `CountryCode`, `Type`, `Prefix` and
`SourcePhoneNumberArn` all require replacement. Only `Description`, `Tags` and `TargetArn`
update in place. A replacement claims a new number and releases the old one.

That is why `#stack-split` puts the number in `ConnectCore`, the long-lived stack, beside the
instance and the email address. `ConnectRouting` is replaced in parts all the time. That is its
purpose, and it is the wrong place for anything that cannot come back. The rule is not "never
change the number". The rule is that a change to the number is a deliberate act in a stack you
deploy rarely, and you read the `cdk diff` before you deploy it.

**The number is a US DID, whatever region your instance is in.** A DID (direct inward dial)
number is an ordinary geographic number. Your instance is in the region you chose in lesson
`00-instance-and-first-agent`, possibly an EU region. Since July 2023 an instance can claim
numbers from outside its own region without an opt-in, and US local and toll-free numbers need
no documents. Many other countries do not work like this. Their regulators require a local
address and identity documents before a number is issued. You make the request through an AWS
Support case, and the AWS documentation says it often takes weeks. Germany is one example. The
AWS page "Region requirements for ordering and porting phone numbers" lists the requirements per
country. A course that told you to claim a number in your own country could stop you at this
lesson for weeks, on paperwork that teaches nothing about Connect. So the course always claims a
US number (`#instance-choices`). Three costs come with that, and the course states them:

- **Each test call from outside the US is an international call** from your own phone, at your
  plan's rate. A VoIP app or a plan with cheap US calls makes this cheaper. The course does not
  recommend a particular one.
- **Latency.** AWS recommends numbers and agents in the instance's region. A US number on an EU
  instance works, but the audio path can exceed 500 ms. You may notice a short delay when you
  talk to yourself through the softphone. That is acceptable for a course and would not be for
  production. A production contact centre in such a country claims local numbers, completes the
  regulatory process once, and keeps the numbers.
- **The number bills every day it exists.** The AWS pricing appendix lists a daily charge for a
  US DID, and a per-minute charge for inbound calls on top of the per-minute voice usage. The
  amounts are small, but they do not stop when you stop working. `COURSE.md`, *When you are
  finished*, says how to release the number at the end, and which step comes first.

**A voice flow is a different program from an email flow, on the same routing.** The two
channels share hours of operation, queues, routing profiles and, in the next lesson, the lookup
Lambda. They do not share a flow, because several blocks behave differently by channel. The
channel tables in the flow block reference show this:

- **Play prompt** supports voice. An email contact routed to it takes the **Error** branch. It
  plays an audio prompt or speaks text through Amazon Polly (text-to-speech, plain text or
  SSML). For voice it is the main block of the flow. For email it does nothing useful.
- **Get customer input** (lesson `07-voice-menu-and-caller-lookup`) supports voice and does not
  support email.
- **Send message**, which sends the automatic acknowledgement in your email flow, accepts voice
  contacts. But your acknowledgement sends to the System key *Customer endpoint address*. On a
  call that key holds the caller's phone number, not an email address. Do not copy the block
  across without thinking. If you want to see what happens, read the flow log.
- **The email subject**, `$.SegmentAttributes['connect:EmailSubject']`, does not exist on a call.
  A rule from lesson `03-flow-logic-for-email` that branches on it takes the no-match branch on
  every call, without an error.
- **Check hours of operation**, **Set working queue**, **Transfer to queue**, **Set contact
  attributes** and **AWS Lambda function** work on both channels. That is the shared part.

You could build one flow that branches on the system attribute `Channel` at the start. The course
uses two files, `flows/inbound-email.json` and `flows/inbound-voice.json`. Each is easier to
read, the email address and the phone number are associated separately anyway, and a change to
the voice greeting cannot break email.

**A number runs a flow only when something associates them.** This is the same pattern as the
email address in lesson `01-first-email-contact`. `AWS::Connect::PhoneNumber` has no property
that names a flow. The link is the `AssociatePhoneNumberContactFlow` API (`PhoneNumberId`,
`InstanceId`, `ContactFlowId`), and its inverse is `DisassociatePhoneNumberContactFlow`. No
CloudFormation resource exists for it, so you make it an `AwsCustomResource`. It goes in
`ConnectRouting`, because it joins a long-lived resource (the number) to a churning one (the
flow), and only the churning stack may know about both (`#stack-split`). `onCreate` and `onUpdate`
associate, so a replaced flow is associated again on the next deploy. `onDelete` disassociates,
so that destroying the routing stack leaves the number clean and not pointing at a deleted flow.

**Voice also needs the instance and the routing profile to allow it.** On the instance, the
attribute `InboundCalls` must be on. Lesson `00-instance-and-first-agent` may have set it already.
Check your code, do not assume. In the routing profile, two separate things must be present, the
same pair that lesson `02-hours-queues-routing-profiles` taught for email:

- a **media concurrency** for `VOICE`, which says that agents with this profile take calls at
  all. For voice the concurrency must be exactly 1. The CloudFormation reference gives the valid
  range for `VOICE` as minimum 1 and maximum 1, because an agent has one voice.
- a **queue configuration** for the course queue on the `VOICE` channel. A queue configuration is
  a pair of queue and channel. The `EMAIL` entry you already have does not cover calls. The admin
  guide says that the channel on a queue entry must also be enabled in the channel settings, or
  contacts on that channel are not routed to agents.

If either is missing, nothing fails at deploy time. The call is answered by your flow, goes into
the queue, and waits there. Your agent shows Available and is never offered the call. This is the
voice version of the email failure in lesson `01-first-email-contact`, and you will recognise it.

**The agent takes the call in the agent workspace.** The user's phone configuration (`PhoneType`
in `PhoneConfig`) decides whether a call rings the browser softphone (`SOFT_PHONE`) or a desk
phone. For this course it must be the softphone, and the browser must be allowed to use the
microphone. The call is offered in the same workspace where you accepted emails. An email and a
call look different there, which lesson `08-one-agent-two-channels` uses.

## Concepts to teach

Claiming a number as renting a real-world resource, and why a replacement releases a number that
cannot be claimed back; which `CfnPhoneNumber` properties force replacement (`CountryCode`,
`Type`, `Prefix`, `SourcePhoneNumberArn`) and which do not; the claim/release quota and the
180-day cool-down; why the number lives in `ConnectCore` (`#stack-split`); a DID number as
distinct from toll-free; why the course's number is US whatever the instance region, the
regulatory requirements many countries attach to local numbers, and the support case and wait
they cause (`#instance-choices`); the international-call cost, the latency note (an out-of-region
number can exceed 500 ms) and the daily number charge, with the teardown pointer to `COURSE.md`;
the inbound voice flow as a separate program on shared routing; text-to-speech in Play prompt;
which blocks differ by channel (Play prompt and Get customer input are not for email; Send
message's *Customer endpoint address* is a phone number on a call; the email subject attribute is
absent on a call); the phone-number association as an `AwsCustomResource` in the churning stack,
with associate on create and update and disassociate on delete; the `InboundCalls` instance
attribute; `VOICE` media concurrency (always 1) and a `VOICE` queue configuration as two separate
requirements; the softphone in the agent workspace.

## Constraints

- You write every construct and draw the flow yourself. The tutor states what is required and
  checks the result. It does not write your stacks or your flow.
- The number is a `CfnPhoneNumber` in `ConnectCore`: `CountryCode` `US`, `Type` `DID`,
  `TargetArn` the instance ARN. It is never in `ConnectRouting`. Do not set a `Prefix` unless you
  have a reason, and never change `CountryCode`, `Type` or `Prefix` on a deployed number without
  reading the `cdk diff` and deciding to lose the number.
- `ConnectCore` publishes `PhoneNumber` (the number in E.164) and `PhoneNumberId` (its id or
  ARN) as `CfnOutput`s with exactly those ids. The checks read them.
- The voice flow lives in `flows/inbound-voice.json`. Every ARN in it is a `${Name}` placeholder,
  substituted with `Fn.sub` at synth, the same way as the email flow (`#flow-round-trip`). The
  flow is a `CfnContactFlow` of type `CONTACT_FLOW` in `ConnectRouting`, which publishes its id as
  `InboundVoiceFlowId`.
- The association is an `AwsCustomResource` in `ConnectRouting`, calling
  `AssociatePhoneNumberContactFlow` on create and update and `DisassociatePhoneNumberContactFlow`
  on delete. Its IAM policy is scoped to what it calls, not `*` on every Connect action.
- References still go one way: `ConnectRouting` reads the number from `ConnectCore`. Nothing in
  `ConnectCore` refers to the flow.
- The voice flow uses the same hours and the same course queue as email. Do not create a voice
  queue. Sharing the queue is the point of the lesson.
- The flow contains a Set logging behavior block, so that a call that goes wrong leaves a flow
  log.
- No menu, no Lambda call, no caller lookup in this lesson. Those are lesson
  `07-voice-menu-and-caller-lookup`.

## Suggested progression

Start with the decision, not the code. Ask the learner where the number goes and why. If they say
`ConnectRouting` ("it is part of routing, isn't it?"), do not correct them yet. Have them declare
it there, synthesize, and then make one change that a learner might plausibly make later, such as
adding a `Prefix` to choose an area code. Have them run `cdk diff ConnectRouting` and read the
line for the phone number: it is a replacement. Then ask them to read the "Release a phone
number" page of the admin guide and tell you what a replacement does to the old number. **Do not
deploy this.** A released number is not reclaimable, and claims count against a quota. The diff
is enough to make the point. Then move the construct to `ConnectCore`, where the same `cdk diff`
discipline applies before every deploy of that stack.

Next, the country. A learner outside the US may ask why not a local number. Have them look up
their own country in the AWS page "Region requirements for ordering and porting phone numbers",
and tell you what it asks for. Do not let them open a support case. The point is to see why the
course chose a US DID (`#instance-choices`), and what a production contact centre in their
country would have to do instead. Then name the three costs: the international call, the
latency, and the daily charge. Point at `COURSE.md`, *When you are finished*, now, so they know
where the teardown is before they rent anything.

Write the `CfnPhoneNumber` and the two outputs, and a test in `tests/` that asserts on the core
template: the resource exists in `ConnectCore`, `CountryCode` is `US`, `Type` is `DID`, and
`ConnectRouting` contains no `AWS::Connect::PhoneNumber`. Have them confirm `InboundCalls` is on
in the instance attributes. Then deploy `ConnectCore` (read the diff first). Look at the
`PhoneNumber` output: they now own a real number. Have them note that a US number dialled from
abroad needs the international prefix for `+1`.

Now the flow. In the console flow designer, have them create an inbound flow and draw it. Use the
email flow as the reference for the shared blocks, and do not copy it. The flow is: Set logging
behavior; a Play prompt with text-to-speech (a short greeting they write); the same Check hours of
operation as the email flow; on the in-hours branch, Set working queue to the course queue, then
Transfer to queue; on the out-of-hours branch, a Play prompt that says they are closed, then
Disconnect / hang up. Wire every Error branch somewhere deliberate. A spoken apology and a
disconnect is fine for now. If the email flow sets `route_reason`, set it here on each path too,
with the values they used for email (`default`, `out-of-hours`), so a call's contact record reads
like an email's.

Before they export, ask what would happen if they had pointed the number at
`flows/inbound-email.json`. Have them answer from the channel tables of the blocks that flow
contains (Send message to *Customer endpoint address*, Check contact attributes on the email
subject), not from guessing. If they want to see it, they can associate the email flow with the
number by hand in the console for one test call, read the flow log, and then remove that
association again. Any association made in the console is replaced at the next deploy anyway.

Export the flow. Save it as `flows/inbound-voice.json`, replace every ARN with a placeholder from
the course's convention (`${CourseQueueArn}`, `${HoursArn}`, and any other they find), and grep
the file for `arn:aws` until the result is empty. Load it in `ConnectRouting` through `Fn.sub`
exactly as the email flow is loaded, as a `CfnContactFlow`, and publish `InboundVoiceFlowId`.
The flow's id comes from its ARN, as in lesson `01-first-email-contact`. Add a test that the
voice flow's content contains no literal ARN and that the flow is of type `CONTACT_FLOW`.

Write the association `AwsCustomResource`. Have them read the request syntax of
`AssociatePhoneNumberContactFlow`. The phone number id is in the URI, and the instance and flow
are in the body. Decide which form of each identifier to pass from what the stacks expose, and
let the first deploy confirm it. Give it `onCreate` and `onUpdate` to associate and `onDelete` to
disassociate, and ask them to explain what goes wrong without `onUpdate` when the flow is
replaced, and without `onDelete` when the routing stack is destroyed.

Now let them ring the number before they touch the routing profile. Agent Available in the
workspace, call the number. They should hear the greeting, and then wait. Nobody is offered the
call. This is the instructive failure: the routing profile has no voice. Have them find the
evidence before the fix. The flow log shows the transfer to queue succeeded. The contact search,
or the real-time metrics for the queue, shows a voice contact waiting. The routing profile, read
from the template or with the CLI, lists `EMAIL` only. Hang up. Then add both halves: a `VOICE`
media concurrency of 1 (have them try 2 in a synth or a test first and read what the
CloudFormation reference says about the range), and a `VOICE` queue configuration for the course
queue. Add a test for each half. Have them say why one half without the other still fails.

Deploy `ConnectRouting`, set the agent Available, and call again. The workspace offers the call,
the agent accepts it, and they hear themselves through the softphone. Note the delay. That is the
latency from `#instance-choices`, and they should name it. Hang up, close the contact, and look at
the contact record: channel `VOICE`, the course queue, the agent, and `route_reason` if they set
it. Then ask the tutor to run the checks.

If time allows, show the out-of-hours branch on demand, the way lesson
`02-hours-queues-routing-profiles` did for email: change the hours in code, deploy, call, hear the
closed message, and restore the hours. Do not wait for the evening.

## Completion conditions

- `cdk-synth` passes, and `pytest` passes with tests that assert: a `CfnPhoneNumber` with
  `CountryCode` `US` and `Type` `DID` in `ConnectCore` and none in `ConnectRouting`; the voice
  flow in `ConnectRouting` of type `CONTACT_FLOW` whose content contains no literal ARN; the
  association custom resource in `ConnectRouting`; and a routing profile with a `VOICE` media
  concurrency of 1 and a `VOICE` queue configuration for the course queue.
- `ConnectCore` publishes `PhoneNumber` and `PhoneNumberId`. `ConnectRouting` publishes
  `InboundVoiceFlowId`. `flows/inbound-voice.json` exists and deploys from the repository.
- The learner has called the number. The voice flow answered, the call went through the same
  hours check and into the same course queue as email, and the agent accepted it in the
  workspace. The `call-routed` validator passes. It reads the deployed number, its flow
  association and the record of the learner's most recent call back from the account. **Place
  the test call first**, so there is a contact for it to read.
- The learner can explain, without notes: why the number is in `ConnectCore` and what a
  replacement would do to it; why the number is US and what a local number would have cost them;
  two blocks that differ between the email flow and the voice flow and why; and why a call to a
  routing profile without `VOICE` waits and is never offered.
- The learner knows where the teardown is (`COURSE.md`, *When you are finished*) and that the
  number bills daily until it is released.

## On completion, persist

Record in the instance's `STATE.md` (and in `DESIGN.md` where it is a durable decision):

- The claimed number in E.164 and the fact that it is a US DID in `ConnectCore`. Record any
  `Prefix` chosen, so a later session does not "tidy" it into a replacement.
- That the number bills daily from the date of the claim, and that releasing it is step 1 of
  `COURSE.md`, *When you are finished*.
- The voice flow's shape (greeting, hours check, working queue, transfer, out-of-hours prompt and
  disconnect) and the placeholder names it uses.
- The association custom resource, and the identifier forms that the deploy showed
  `AssociatePhoneNumberContactFlow` accepts.
- That the routing profile now carries `VOICE` concurrency 1 and a `VOICE` queue configuration
  for the course queue. Do not record chosen concurrency numbers for email as final. Lesson
  `08-one-agent-two-channels` decides them.
- The latency the learner noticed, in their own words, as a known property of this set-up.

## Optional deeper paths

- Add a **customer queue flow** (Set customer queue flow, a flow of type `CUSTOMER_QUEUE`) so a
  waiting caller hears something you chose instead of the default, and export it with the same
  round trip.
- Use **SSML** in the greeting to control pauses and pronunciation, and **Set voice** to choose
  the Polly voice and language. The admin guide lists the SSML tags Connect supports.
- Compare a **toll-free** number with a DID: what it costs per minute, who pays for the call, and
  why it is not the course default.
- Read the **regulatory requirements** for the learner's own country in full, and sketch what a
  production set-up there would need: who files the documents, how long it takes, and why that
  number would also live in a long-lived stack, or outside CloudFormation altogether.
- Look at **traffic distribution groups**, which claim numbers to a group spanning two regions
  instead of to one instance, and why `TargetArn` accepts either.
