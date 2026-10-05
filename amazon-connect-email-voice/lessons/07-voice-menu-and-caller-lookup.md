---
id: 07-voice-menu-and-caller-lookup
title: Voice menu and caller lookup
design_refs: [lambda-contract, flow-round-trip]
validators: [cdk-synth, pytest, lambda-enriches, call-routed]
---

## Purpose

Give callers a touch-tone menu, and recognise known callers with the same Lambda that already recognises email senders.

After lesson `06-a-phone-line` every call goes the same way: a greeting, the hours check and the
course queue. The email flow already makes decisions. It acknowledges, it routes on a rule, and it
asks the lookup Lambda who is writing. In this lesson the voice flow catches up in the voice way.
A caller is offered a **menu** and chooses with the keypad. A caller who presses nothing still
reaches an agent. A **known caller** is recognised from their phone number by the **same lookup
Lambda** from lesson `04-lambda-enrichment`, greeted by name, and sent to the priority queue. The
Lambda does not change. If it has to, the contract from lesson 04 was shaped around email, and
this lesson is where you find that out.

## Prerequisites

- Lesson `06-a-phone-line` is complete. The US number is claimed in `ConnectCore`,
  `flows/inbound-voice.json` deploys from the repository and is associated with the number, and
  your agent accepts calls in the workspace.
- Lesson `04-lambda-enrichment` is complete. The lookup Lambda (`LookupFunctionName`), its table
  (`CustomersTableName`), the `LAMBDA_FUNCTION` integration association and the resource-based
  permission for `connect.amazonaws.com` are deployed. `tools/load_customers.py` is in the
  workspace.
- The priority queue from lesson `03-flow-logic-for-email` (`PriorityQueueId`).
- Flow logs and Lambda logs, and the habit from lesson `05-following-a-contact` of reading them
  before guessing.

## Learning objectives

- Build a DTMF menu with **Get customer input**: a text-to-speech prompt, a condition per key,
  and deliberate wiring of the **Timeout**, **Default** and **Error** branches
- Explain what a silent caller does to a menu with no timeout handling (it loops or it drops),
  and design a menu that repeats at most a bounded number of times and then routes the caller
  anyway
- Invoke the lesson 04 lookup Lambda from the voice flow, keyed on the caller's number, without
  changing the function or its contract (`#lambda-contract`)
- Explain why the caller's number is normalised in exactly one place, the Lambda, and never in
  the flow
- Recognise your own non-US caller ID in E.164 form and add it to the table with the supplied
  loader
- Copy the Lambda's result onto the contact as attributes, greet a known caller by
  `display_name` in a text-to-speech prompt, and set `route_reason` on every path
- Show from the contact record and the logs which path a call took and why

## Theory

**Get customer input is a menu, and a menu is a loop waiting to happen.** The block plays a
prompt, waits for the caller to press a key, and branches. In DTMF mode it accepts single digits
0 to 9, `#` and `*`. You add one **condition** per key you offer (for example *1* and *2*), and
the block also has three branches you do not choose to have:

- **Timeout**: the caller pressed nothing within **Set timeout**. The value is static, at least 1
  second and at most 180 seconds, and for voice it counts until the first digit.
- **Default**: the caller pressed a key that matches no condition.
- **Error**: the block failed.

The block supports voice. It does not support email, which is one more reason the two channels
have separate flows. The usual thing to do with Timeout and Default is to play the menu again. If
you wire them straight back to the same block, a caller who has put the phone down on the table,
or a caller whose keypad tones do not arrive, hears the menu for ever. Connect keeps the call open
and keeps billing per minute. If you wire them to **Disconnect / hang up**, the silent caller is
dropped, and that is the caller who needed an agent most. The design that works is a bounded
retry: play the menu again a fixed number of times (the **Loop** block counts for you), and then
route the caller to the course queue as if they had chosen the general option. A caller who
presses nothing reaches an agent. That is one of this lesson's completion conditions.

**Each key is a routing decision, so each one sets `route_reason`.** The menu choices are yours.
A reasonable shape is *1* for a general or billing question, which goes to the course queue, and
*2* for something urgent, which goes to the priority queue. Each path then sets `route_reason` to
a short string that says why the queue was chosen, as the email flow does since lesson
`03-flow-logic-for-email`: for example `menu-billing`, `menu-urgent`, `no-input`, `tier-gold`,
`lookup-error`. Lesson `05-following-a-contact` showed why. The contact record is the evidence,
and a contact without a reason cannot be explained later.

**The lookup Lambda already serves voice, if lesson 04 honoured the contract.** `#lambda-contract`
says one function serves both channels. Its input is the contact's customer endpoint from the
Connect event (`Details.ContactData.CustomerEndpoint.Address`). For an email that is the sender's
address. For a call it is the caller's number, with `CustomerEndpoint.Type` `TELEPHONE_NUMBER`.
The function branches on `Details.ContactData.Channel` (`VOICE` or `EMAIL`), because the endpoint
type for email is not documented. It normalises the endpoint in one place. It returns a flat map
of strings (`customer_id`, `tier`, `display_name`), or an empty map for an unknown customer, and
it raises on error. The flow invokes it synchronously with response validation `STRING_MAP`,
with a timeout below the 8-second maximum for synchronous invocations.

So the voice flow needs **no new Lambda and no new grant**. The `LAMBDA_FUNCTION` integration
association and the resource-based permission are made per instance and per function, not per
flow. The voice flow invokes the same function, through the same `${LookupFunctionArn}`
placeholder. If you notice that you want a second function "for phone numbers", stop. That is
the instructive failure, and the contract exists to prevent it. If a call shows that the function
does not handle voice, the fix goes into the one function, in its normalisation. The email tests
from lesson 04 must still pass afterwards.

**Your own caller ID is the normalisation case.** The table is keyed on the normalised endpoint
(`endpoint`): a lower-cased email address, or an E.164 phone number. E.164 is `+`, the country
code and the subscriber number, with no spaces, no leading zero for the trunk prefix and no
punctuation, for example `+4917012345678`. The seed records use reserved numbers. To be
recognised, you add a record with your own number using `tools/load_customers.py` (supplied in
lesson `04-lambda-enrichment`):
`python3 tools/load_customers.py --add-endpoint <your number in E.164> --tier gold --name
"<a name>"`. Use a name in the form your display-name experiment in lesson
`04-lambda-enrichment` showed survives the trip to Connect. This is your personal data, in your
own account. It is deleted at teardown (`COURSE.md`, *When you are finished*), and you remove it
yourself with `--remove-endpoint`.

Two things can go wrong here, and both look like "the lookup said unknown". First, the form of
the number. The number you know as `0170 1234567`, or `+49 170 1234567` with spaces, is not the
string Connect sends, and not the string a correct normaliser produces. Second, what Connect
actually sends for a call that crosses networks from abroad to a US DID. The documentation says
the attribute holds "the customer's phone number". It does not show the format for every case.
**Do not assume. Read it.** The Lambda log for your test call shows exactly the event that
arrived. The normalised form that the function computes, and the form the loader stored, must be
the same string. If they differ, make them agree in the one place that owns normalisation. Never
put a transformation in the flow (a Set contact attributes block that rewrites the number, or a
Lambda input parameter that pre-formats it). A flow that normalises is a second normaliser. The
next channel, or the next flow, will not do it the same way, and the email path never does it at
all.

**The Lambda's answer is not a contact attribute until you copy it.** The AWS Lambda function
block returns its key-value pairs as Lambda result attributes. The admin guide references them as
`$.External.<key>` in text-to-speech examples and as `$.LambdaInvocation.ResultData.<key>` in the
attribute list. Either way they are overwritten by the next invocation, they are not in the
contact record, and they are not shown to the agent. A **Set contact attributes** block copies
them into user-defined attributes (`$.Attributes.<key>`). From that point they are in the contact
record and in the workspace. Your email flow already does this if lesson 04 is complete. The voice
flow needs the same copy. Then a **Play prompt** can greet the caller with text-to-speech that
contains the reference, for example `Hello $.Attributes.display_name, thank you for calling.`.
Connect fills in the value when it speaks.

An **unknown** caller has no `display_name`. Do not try to work out what Polly says for a missing
attribute. Find out on one test call, and then design so that it cannot happen. Branch with
**Check contact attributes** on whether the lookup found someone (for example on `tier`), and
greet by name only on the branch where a name exists.

## Concepts to teach

Get customer input in DTMF mode: single-key conditions, the static timeout (1 to 180 seconds),
and the Timeout, Default and Error branches; the silent caller, and why wiring Timeout back to the
menu loops and wiring it to a disconnect drops; a bounded retry (the Loop block) that ends in the
course queue; a menu choice as a routing decision with its own `route_reason`; the lookup Lambda
reused unchanged for voice (`#lambda-contract`): the endpoint from `CustomerEndpoint.Address`,
branching on `Channel`, the flat `STRING_MAP` response, synchronous invocation under 8 seconds, and
the Error and Timeout branches of the Lambda block; that the integration association and the
invoke permission are per instance and function, so voice needs no new grant; E.164, the learner's
non-US caller ID as the normalisation case, and normalisation in one place only; adding the
learner's own number with `tools/load_customers.py` as personal data deleted at teardown; Lambda
result attributes versus user-defined contact attributes, and copying with Set contact
attributes; a text-to-speech greeting that references `$.Attributes.display_name`, with a branch
so an unknown caller is never greeted by a missing name; reading the Lambda log to see exactly
what Connect sent.

## Constraints

- You draw the flow and write any code yourself. The tutor does not write your flow, your
  Lambda or your tests.
- **The voice flow invokes the same lookup Lambda as the email flow.** No second function, no
  voice-only copy, no wrapper. The function's contract (`#lambda-contract`) does not change. If
  the function needs a fix to serve voice, the fix goes into its one normalisation path, and the
  lesson 04 tests and the email behaviour still pass.
- **The flow never transforms the phone number.** No Set contact attributes block or Lambda input
  parameter that reformats the caller's number. Normalisation lives in the function.
- The menu has a bounded retry. No branch of Get customer input is wired back to the same block
  without a counter, and no branch drops a caller who pressed nothing. A caller who presses
  nothing reaches the course queue.
- Every path that reaches a Transfer to queue has set `route_reason` first. The Lambda's Error
  and Timeout branches route the caller to the course queue with their own `route_reason`. A
  lookup failure never strands a caller.
- The menu choices, their keys and the `route_reason` strings are yours to choose, and you
  record them. At least one choice routes to the priority queue, and at least one to the course
  queue.
- `flows/inbound-voice.json` stays placeholder-only (`${LookupFunctionArn}`,
  `${PriorityQueueArn}`, `${CourseQueueArn}`, `${HoursArn}`), and every change is made in the
  designer, exported, and deployed from the file (`#flow-round-trip`).
- The routing profile needs a `VOICE` queue configuration for the priority queue as well, or
  urgent and gold callers wait unoffered, as in lesson `06-a-phone-line`.
- Your own record is added with `tools/load_customers.py`, never by hand-editing the table in
  the console, and it is removed at teardown.

## Suggested progression

Start from the call the learner will make. Ask them for their own number in E.164 and have them
write it down, without spaces and with the country code. Then ask what string they think Connect
will put in `CustomerEndpoint.Address` when they call the US number from their phone. Do not
answer it. The Lambda log will.

Draw the lookup first, before the menu. In the designer, open the voice flow (re-import the file
if the console copy has drifted from it), and after Set logging behavior add the AWS Lambda
function block: the lookup function, synchronous, response validation `STRING_MAP`, a timeout
below 8 seconds. Then add a Set contact attributes block that copies `customer_id`, `tier` and
`display_name` onto the contact. Wire the Lambda's Error and Timeout branches to Set working queue
on the course queue with `route_reason` set to a lookup-failure value. Export, replace the ARNs,
deploy, and call **before** adding the learner's own record. They are an unknown caller. The flow
should take the success branch with an empty result. Have them open the Lambda's log for that
invocation, find `Details.ContactData.CustomerEndpoint.Address` and `Channel`, and compare the
number with what they wrote down.

Now add their record: `python3 tools/load_customers.py --add-endpoint <their E.164> --tier gold
--name "<their name>"`. Before calling again, have them read what the loader stored (in the
table, or in the loader's code) and what the function will compute from the logged address.
Are the two strings the same? If they are, call and expect a match. If they are not, this is the
normalisation lesson. Ask where the fix belongs. If the answer is "in the flow", ask what the email
path, or the next flow, would then do differently, and bring them back to the function. Any fix
goes into the function's normaliser with a unit test that covers the logged form, and the email
tests from lesson 04 must still pass. If the function needed no change, say so explicitly: the
contract held.

Then the branch on who called. After the copy, add Check contact attributes on `tier`. For `gold`
(the learner's own record), a Play prompt with text-to-speech greets them with
`$.Attributes.display_name`, sets `route_reason` (for example `tier-gold`), Set working queue to
the priority queue, then the hours check and Transfer to queue. Everyone else goes to the menu. If
the learner wants to hear what happens when a name is missing, let them greet the no-match branch
by name for one test call, then fix it.

Then the menu, for callers who are not gold. Get customer input with a text-to-speech prompt
that names the keys, DTMF conditions for the keys they chose, and a Set timeout of a few seconds.
Each condition sets its own `route_reason` and working queue. Before wiring Timeout and Default,
have them wire Timeout straight back into the same Get customer input block, deploy, call as an
unknown caller (remove their record with `--remove-endpoint`, or call from a second phone), and
press nothing for about half a minute. They hear the menu again and again. Ask what a caller who
had put the phone down would cost, and who would help them. Hang up. Then build the bounded retry
with the Loop block (two plays is plenty), and after it route to the course queue with a
`no-input` reason. Wire Default (a wrong key) into the same retry, and Error to the course queue.
Export, deploy, and test each path: key 1, key 2, a wrong key, and silence. After each test call,
look at the contact record's attributes and confirm the `route_reason` matches the path.

Check the routing profile has a `VOICE` queue configuration for the priority queue. If the key-2
call waits unoffered, the learner has seen this failure before in lesson `06-a-phone-line` and
should find it from the evidence in under a minute.

Finally, put the learner's gold record back (`--add-endpoint` again) and make the call the
validators read: the known caller, greeted by name and routed to the priority queue. Then ask the
tutor to run the checks.

## Completion conditions

- `cdk-synth` passes, and `pytest` passes with tests that assert: the voice flow's content
  references the lookup function only through the placeholder and contains no literal ARN; the
  stacks still declare exactly one lookup function; the routing profile has `VOICE` queue
  configurations for both the course queue and the priority queue; and, if the function's
  normaliser changed, a unit test that covers the caller-ID form the learner observed, with the
  lesson 04 tests still passing.
- A call from the learner's own number, whose record they added with
  `tools/load_customers.py`, is recognised by the same Lambda that serves email. The caller is
  greeted by `display_name`, `customer_id`, `tier` and `display_name` are on the contact's
  attributes, and the call is routed to the priority queue with its `route_reason`. The
  `lambda-enriches` and `call-routed` validators pass. **Make that call last**, so it is the most
  recent call the validators read.
- The learner has shown, by test calls, that a menu choice changes the queue, and that a caller
  who presses nothing reaches the agent after a bounded number of repeats. For each test they can
  point at the `route_reason` on the contact record that proves the path.
- The learner can explain, without notes: why the Timeout branch must not loop unbounded or drop
  the caller; why there is one Lambda and where normalisation lives; what string Connect sent as
  their caller ID, from the Lambda log; and why a Lambda result is copied into contact attributes
  before the greeting and the record can use it.

## On completion, persist

Record in the instance's `STATE.md` (and in `DESIGN.md` where it is a durable decision):

- The menu: each key, the queue it routes to, and its `route_reason`; the timeout value and the
  number of repeats before a silent caller is routed to the course queue.
- The full set of `route_reason` values the voice flow uses, beside the email flow's, so lesson
  `08-one-agent-two-channels` and any later tracing can read a contact's reason without opening
  the flow.
- The exact form in which Connect delivered the learner's caller ID, as seen in the Lambda log,
  and whether the function's normaliser needed a change to match it. If it did, record the change
  as an amendment that keeps `#lambda-contract`, not as a new contract.
- That the learner's own phone and email records are in the table (personal data in their own
  account), added with `tools/load_customers.py`, and are to be removed with `--remove-endpoint`
  at teardown.
- That voice and email now share hours, both queues and one lookup Lambda, and that lesson
  `08-one-agent-two-channels` decides what one agent is offered when both channels are waiting.

## Optional deeper paths

- Use **Store customer input** to take a multi-digit entry, such as a customer number for
  callers whose phone number is unknown. Discuss why the lookup would then need a second key, and
  what that does to the contract.
- Enable **touchtone buffering** (Set Touchtone Buffer Behavior) so returning callers can type
  ahead of the prompt, and see how it changes Get customer input and Play prompt.
- Replace the keypad with an **Amazon Lex** bot in Get customer input. Lex bot authoring is out of
  scope for the course, but the block's Lex mode and its session-attribute timeouts are worth
  reading.
- Consider what the lookup should do when a caller **withholds their number**. Find out on a test
  call what arrives in `CustomerEndpoint.Address`, and decide whether the function's empty result
  is already the right answer.
- Read about **Customer Profiles** and the Customer profiles block, which is the managed version
  of the lookup this course builds by hand.
