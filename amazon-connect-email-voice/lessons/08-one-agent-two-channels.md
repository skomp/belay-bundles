---
id: 08-one-agent-two-channels
title: One agent, two channels
design_refs: [stack-split, deliberately-unresolved]
validators: [cdk-synth, pytest, concurrency-observed]
---

## Purpose

Decide what one agent is offered when a call and emails are waiting at the same time, then predict the order and prove the prediction.

Each channel now works on its own. An email reaches your agent, and a call reaches your agent.
A real agent is rarely so lucky. Calls and emails arrive together, and the routing profile
decides what the agent is offered first, how many contacts the agent may hold, and whether a
call can arrive while the agent is writing an email. Until now you set those values just to make
each channel work. In this lesson you choose them on purpose. You set concurrency per channel,
cross-channel behaviour and queue priority and delay. Then you write down a prediction of the
order in which the agent is offered one call and two emails, before you test. Then you test,
and explain what you see from the routing profile alone.

## Prerequisites

- Lessons `06-a-phone-line` and `07-voice-menu-and-caller-lookup` are complete. Calls and emails
  both reach your agent, through the course queue and the priority queue, and every contact
  carries a `route_reason`.
- The routing profile in `ConnectRouting` has `VOICE` and `EMAIL` media concurrencies and queue
  configurations for both queues on both channels.
- Your own mailbox, to send the test's two emails by hand. You choose each email's sender and
  subject so that you know which queue it will reach. Do not use `tools/scenarios.py` from lesson
  `05-following-a-contact` here: it always creates three contacts, and two of them go to the
  priority queue, so it cannot set up the test this lesson needs.
- Your phone, for one call that you keep on hold for a minute or two. From outside the US that is
  an international call. Keep tests short.

## Learning objectives

- Explain **media concurrency**: per channel, how many contacts an agent can hold at once. Voice
  is always 1, and email is a choice up to 10
- Explain **cross-channel behaviour**, which is set per channel (`ROUTE_CURRENT_CHANNEL_ONLY` or
  `ROUTE_ANY_CHANNEL`), and apply it to the case "the agent is on a call and an email arrives" and
  to the opposite case
- Explain **queue priority and delay**. They are set per queue and channel pair in the routing
  profile, not on the queue. Priority takes precedence. A delay holds a contact back from this
  profile's agents until it is old enough. With equal priority and delay, the oldest contact is
  offered first
- Configure all three in CDK, as `MediaConcurrencies` and `QueueConfigs` on the routing profile,
  and test them against the template
- Choose concurrency numbers for this contact centre and defend them. The course does not
  prescribe them
- Predict the offer order of a mixed set of waiting contacts, write the prediction down before
  testing, observe, and explain any difference from the routing profile
- Explain, without building it, where agent assist and generative self-service from AI agents in
  Amazon Connect would sit in your own email and voice flows

## Theory

**A routing profile answers three questions for every agent who has it.** What channels do they
take, and how many contacts of each at once? While they hold a contact on one channel, can they
be offered a contact on another? When contacts wait in several queues, which one comes first?
CloudFormation gives the answers as two lists on `AWS::Connect::RoutingProfile`:
`MediaConcurrencies` and `QueueConfigs`.

**Media concurrency is per channel.** Each `MediaConcurrency` names a `Channel` (`VOICE`,
`CHAT`, `TASK` or `EMAIL`) and a `Concurrency`, the number of contacts of that channel an agent
can hold at once. For `VOICE` the only valid value is 1. For email the admin guide allows up to
10. It also notes that an agent may start up to twice that number of outbound emails. A contact
holds its slot until the agent closes it. In the admin guide's worked example, a contact frees
the agent only after the agent "closes ACW", which means after-contact work counts. So a call in
after-contact work still blocks the next call.

**Cross-channel behaviour is also per channel, and it is about the channel the agent is on.**
Each `MediaConcurrency` can carry a `CrossChannelBehavior` with a `BehaviorType` of
`ROUTE_CURRENT_CHANNEL_ONLY` or `ROUTE_ANY_CHANNEL`. In the console these are "No other channels
while agent is on *channel*" and "Allow other channels concurrently". The setting on `VOICE`
answers: while this agent is on a call, may they be offered an email? The setting on `EMAIL`
answers the opposite question: while they work an email, may they be offered a call? The two are
independent. "Calls interrupt emails, but emails never interrupt calls" is one valid design, set
as `ROUTE_ANY_CHANNEL` on `EMAIL` and `ROUTE_CURRENT_CHANNEL_ONLY` on `VOICE`. The admin guide's
worked example shows that Connect checks *every* contact the agent holds. One contact on a
channel that allows nothing else blocks other channels, even when another contact the agent holds
would allow them.

Do not reason from defaults you have not checked. You configured these values earlier just to
make each channel work, or did not configure them. "An agent on a call is offered nothing else"
and "an agent on a call is offered everything" are both guesses until you read the deployed
profile. `aws connect describe-routing-profile` shows what the instance actually holds.

**Priority and delay are set per queue and channel pair, in the routing profile.** Each entry in
`QueueConfigs` is a `QueueReference` (a `QueueArn` and a `Channel`) with a `Priority` (1 to 99,
where 1 is highest) and a `Delay` in seconds (0 to 9999). The queue itself has no priority
property. `AWS::Connect::Queue` has hours, a maximum contact count and outbound settings, and
nothing else that orders contacts. This matters when you want "calls before emails". You cannot
say that on the queue, and you do not need a second queue. The admin guide's answer is to list
the same queue twice in the routing profile, once for `VOICE` with one priority and once for
`EMAIL` with another. Because priority is in the profile, two groups of agents can rank the same
queue differently.

The rules for choosing what to offer one agent, as the admin guide states them in its priority
and delay examples:

- **Priority takes precedence.** A contact in a priority-2 entry is offered only when no
  eligible contact waits in a priority-1 entry. This holds even when the priority-2 contact has
  waited much longer.
- **Delay holds a contact back from this profile's agents** until it has waited that many
  seconds, whether or not the agent is idle. After that, it competes at its entry's priority.
- **With equal priority and delay, the oldest contact goes first.** This is first-in, first-out
  across channels too. The routing-profile guide says that FIFO is still respected while Connect
  evaluates several channels at once.
- **Between agents** (with only one agent, this does not apply to you), Connect offers the contact
  to the agent who holds the fewest contacts across all channels, and then to the one who has been
  Available longest.

A separate lever exists and is easy to confuse with priority. The flow block **Change routing
priority / age** changes one *contact's* priority or apparent age within its queue. It is per
contact, set in a flow. It is not the routing profile's per-queue-per-channel priority, and it is
not the tool for "calls before emails".

**What the agent workspace shows.** A call and an email are offered differently. The call rings
the softphone and must be accepted while the caller waits. The email arrives as a message to read
and answer, and the customer does not wait on the line. Watch for this during the test. It is
part of why a contact centre usually lets calls interrupt email work and not the reverse. It is
not a rule, and your numbers are your own decision (`DESIGN.md`, *Deliberately unresolved*).

**One contact at a time proves nothing about concurrency.** Every test so far had one contact.
With one contact waiting, every configuration routes it to the one Available agent, so a profile
that is wrong for a busy day passes a quiet test. Concurrency, cross-channel behaviour and
priority only show their effect when **several contacts wait at once**, before the agent becomes
Available. That is how this lesson's test is built.

**What AI agents would add to your flows (explained, not built).** Your agent now works two
channels from flows you wrote. AWS's generative AI for this is **AI agents** in Amazon Connect.
It launched as **Amazon Q in Connect**, and that name is still in the API reference and in the
default prompt names; the admin guide's pages now call the service **Connect Customer**. Check the
current names when you read the documentation, because they have changed more than once. AI
agents do two separate jobs:

- **Agent assist** helps your human agent. A **Connect assistant** block in a flow associates the
  contact with an AI agents *domain*, which is one knowledge base. For an email contact, the agent
  then sees in the workspace's Connect assistant panel an overview of the email thread,
  recommended knowledge articles, and a drafted reply to copy, edit and send. In your email flow
  the block would sit before Transfer to queue, behind a Check contact attributes that lets only
  inbound email through. The admin guide warns that an outbound email that reaches the block is
  analysed and charged: the same outbound-flow trap as Send message in lesson
  `03-flow-logic-for-email`. For calls, agent assist also needs **Set recording and analytics
  behavior** with real-time conversational analytics, which this course does not cover.
- **Generative self-service** lets an AI agent talk to the customer directly, and is documented
  for **voice and chat only, not email**. In a voice flow it sits where your menu is: a **Get
  customer input** block invokes a conversational AI (Amazon Lex) bot that hands the conversation
  to the AI agent. When the AI agent stops, for example with its `Escalate` or `Complete` tool,
  control returns to the flow, and a Check contact attributes on the Lex session attribute
  decides what happens next. An escalation still ends in Set working queue and Transfer to queue,
  so it still needs a `route_reason`, and the attributes your lookup copied onto the contact
  before the menu are still there to route on.

The course builds neither: both need a knowledge base and a domain, and self-service needs a Lex
bot, which are outside its scope (`COURSE.md`, *Coverage*). What you can do is say where each one
would plug into the flows you already have.

## Concepts to teach

The routing profile as the answer to three questions (which channels and how many, what may arrive
while busy, and which waiting contact comes first); `MediaConcurrencies` per channel, voice fixed
at 1, email up to 10, and a contact holding its slot through after-contact work;
`CrossChannelBehavior.BehaviorType` (`ROUTE_CURRENT_CHANNEL_ONLY`, `ROUTE_ANY_CHANNEL`) set per
channel and read as "while on this channel"; that Connect checks every contact the agent holds;
`QueueConfigs` as queue and channel pairs with `Priority` (1 highest) and `Delay`; that the queue
has no priority, and listing a queue twice to rank channels differently; priority takes precedence
over age, delay holds a contact back, and FIFO applies at equal priority and delay; the
between-agents rule (fewest contacts, then longest Available) and why it does not matter with one
agent; Change routing priority / age as a per-contact lever, distinct from the profile; how the
workspace presents a call and an email; reading the deployed profile instead of trusting
defaults; why a single-contact test cannot validate concurrency; the concurrency numbers as the
learner's own defended decision (`DESIGN.md`, *Deliberately unresolved*); AI agents in Amazon
Connect (formerly Amazon Q in Connect), explained and not built: agent assist through a Connect
assistant block in the email or voice flow, generative self-service through Get customer input
and a Lex bot in the voice flow only, and the hand-back to the flow's own routing.

## Constraints

- You choose the numbers and the behaviours. The tutor does not propose values. It asks you to
  defend yours, and it checks that your prediction follows from them. The course prescribes
  none of them (`DESIGN.md`, *Deliberately unresolved*).
- Everything is in code in `ConnectRouting`. The routing profile, its `MediaConcurrencies` (with
  an explicit `CrossChannelBehavior` on each) and its `QueueConfigs` are declared in CDK, never
  set in the console. A console change is overwritten at the next deploy, and it would make the
  prediction about something other than the code.
- `VOICE` concurrency is 1. `EMAIL` concurrency is a number you choose and can justify.
- Priority and delay are set in the routing profile's `QueueConfigs`. If you want channels ranked
  differently, list the queue once per channel. No extra queue, and no Change routing priority /
  age block, to do the routing profile's job.
- The routing profile, like the agent user, stays in `ConnectRouting` (`#stack-split`). Nothing in
  this lesson touches `ConnectCore`.
- **The prediction is written down before the test.** You state it to the tutor, who records it
  in `tutorial/STATE.md` before you make any contact Available. A prediction made after watching
  the result is not a prediction.

## Suggested progression

Start by reading, not writing. Have the learner show the routing profile as it is deployed,
`aws connect describe-routing-profile` and its queue list, and say for each channel what its
concurrency and cross-channel behaviour are now. Then ask the two questions this lesson is
about. "You are on a call and an email arrives. Are you offered it?" "You are answering an email
and a call arrives. Are you offered it?" Let them answer from what they read. If they answer
from intuition ("of course not, I'm on the phone"), ask which property of the deployed profile
says so. A behaviour they never set is not something they decided.

Then the decision. Ask what this contact centre should do. One agent, a phone line that charges
the caller by the minute, and an inbox where customers wait patiently. Have them choose an email
concurrency, a `BehaviorType` for `VOICE` and one for `EMAIL`, and a priority and delay for each
queue and channel pair. Ask them to defend each choice in one sentence. If they want "calls before
emails" and try to put a priority on the queue construct, let them look for the property. When
they find there is none, have them read why the admin guide lists a queue twice.

Write it in CDK: an explicit `CrossChannelBehavior` on each `MediaConcurrency`, and one
`QueueConfig` per queue and channel pair. Add tests in `tests/` that assert on the routing
template: `VOICE` concurrency 1, the chosen `EMAIL` concurrency, each `BehaviorType` as chosen,
and the priority and delay of each pair. Deploy `ConnectRouting` and check with
`describe-routing-profile` that the account now holds what the code says.

Now design the test, and make sure it is not a one-contact test. If the learner proposes "send an
email, see that it arrives, then call, see that it arrives", ask what that would show about which
contact is offered first, and about whether the call can arrive during the email. The answer is
nothing, because each contact was alone. The test needs **one call and two emails waiting
together** before the agent is Available:

1. Agent not Available (Offline, or another non-routable status) in the workspace.
2. Decide which queue each email should reach, then send the two emails by hand so that they
   do. Ask the learner how their flow will route each one before they send it. Since lesson
   `04-lambda-enrichment` their own address is a gold record, so every email from it goes to
   the priority queue, whatever the subject. To land one in the course queue they either send
   it from a second mailbox that is not in the table, or remove their own email record for the
   test with `python3 tools/load_customers.py --remove-endpoint <their address>` and let the
   subject rule decide. Note the time each email was sent, wait until both show as contacts in
   queue, and confirm each one's queue and `route_reason` from contact search or
   `describe-contact` before going on. The prediction needs these queues as facts, not guesses.
3. Call the number, take the menu path the learner chooses, and stay on the line in queue. Note
   the time, and name the queue that menu path reaches.

Before step 4, the **prediction**. The learner says, in order, what the agent will be offered
when they go Available: which contact first, whether a second contact is offered while the first
is open, and what happens after each one is closed. For each step they name the property of the
routing profile that decides it: priority, delay, age, concurrency or cross-channel behaviour.
The tutor records the prediction in `STATE.md`. Only then:

4. Set the agent Available. Accept, work and close each offered contact in turn, and note the
   order in which each contact was offered. Do not hold the call longer than you need to, because
   it is an international call.

Compare the observation with the prediction. If they match, ask the learner to explain *why* from
the profile, step by step. A match by luck is still a guess. If they differ, do not let them
change the prediction. Have them find the property they misread. Contact search and the contact
records give each contact's enqueue time, queue and agent, and the flow log shows when each was
queued. Common surprises: an email created a moment later than the call that is still offered
first because of priority or delay; a second email offered during the first because email
concurrency is above 1; or no email during the call because of `VOICE`'s behaviour.

Then the second run, which every learner does. Have them change exactly one routing-profile
setting: the `Priority` or the `Delay` of one queue and channel entry in `QueueConfigs`. They
choose the entry and the new value so that, by their own reasoning, the offer order changes.
Update the template test for that entry, deploy `ConnectRouting`, and confirm the change with
`describe-routing-profile`. Before any contact is created, the learner writes down the new
prediction, with the property that decides each step, and the tutor records it in `STATE.md`.
Then repeat steps 1 to 4 with fresh contacts: the same kinds of email to the same queues, and
the same menu path. Compare again. Two predictions that differ by one property, both correct,
make the strongest evidence; a second run that matches the first when the learner expected a
change is the most useful thing in the lesson, and they find the misread property as before.
Leave the profile at whichever of the two settings the learner defends, and keep the code, the
tests and the deployed profile in agreement.

Close the build with the question the course has deferred until now. Have the learner open
their two flow files and say, block by block, where agent assist would go in the email flow and
in the voice flow, where generative self-service would go in the voice flow, and why it has no
place in the email flow (*Theory*, *What AI agents would add to your flows*). They answer from
their own flows, not from the documentation's diagrams.

End the lesson, and the course, by pointing at teardown. `COURSE.md`, *When you are finished*,
gives the order: release the number first, then destroy `ConnectRouting`, then `ConnectCore`.
Before destroying the routing stack, the learner removes their own records from the table with
`python3 tools/load_customers.py --remove-endpoint <endpoint>` (their phone number, and their
email address from lesson `04-lambda-enrichment` if it is still there), and deletes any copy of
those records they keep outside the account.

## Completion conditions

- `cdk-synth` passes, and `pytest` passes with tests that assert, on the `ConnectRouting`
  template: `VOICE` media concurrency 1; the learner's chosen `EMAIL` concurrency; an explicit
  `CrossChannelBehavior.BehaviorType` on both channels, as chosen; and `QueueConfigs` with the
  chosen `Priority` and `Delay` for each queue and channel pair.
- The deployed routing profile matches the code. The learner shows it with
  `describe-routing-profile`.
- `concurrency-observed`, a manual condition: with **one call and two emails waiting at the same
  time** before the agent went Available, each email sent by hand and its queue confirmed from
  the contact record before the prediction, the agent was offered them in the order the learner
  predicted. This holds for **both runs**: the first, and the second after one `Priority` or
  `Delay` in `QueueConfigs` was changed. Each prediction was recorded in `STATE.md` **before**
  its test. The learner explains
  each step of the observed order from a named property of the routing profile: priority, delay,
  age, concurrency or cross-channel behaviour. A result that differed from the prediction does
  not pass when the prediction is rewritten. It passes when the learner identifies the property
  they misread, corrects the reasoning, and confirms it with a new prediction and test.
- The learner defends their concurrency numbers and behaviours in a sentence each, for this
  contact centre, and can say what they would change for a team of agents.
- The learner can explain, pointing at blocks in their own `flows/inbound-email.json` and
  `flows/inbound-voice.json`, where agent assist (a Connect assistant block) would sit in each
  flow and where generative self-service would sit in the voice flow, why self-service has no
  place in the email flow, and how a contact the AI agent hands back still reaches a queue with a
  `route_reason`.
- The learner knows the teardown order in `COURSE.md`, *When you are finished*, and that their
  own records are removed with `python3 tools/load_customers.py --remove-endpoint`.

## On completion, persist

Record in the instance's `STATE.md` (and in `DESIGN.md`, under *Deliberately unresolved*, as the
learner's resolution for their own contact centre):

- The chosen `EMAIL` concurrency, the `BehaviorType` for each channel, and the priority and delay
  of each queue and channel pair, each with the learner's one-sentence reason.
- Each prediction as recorded before its test, the observed order, and the explanation. Where
  they differed, the property that was misread. For the second run, the one `QueueConfigs`
  setting that was changed, its old and new value, and which value the profile was left at.
- Where the learner placed agent assist and generative self-service in their own flows, in a
  sentence each. Nothing is built.
- That the course's build is complete, and the state of teardown: whether the number has been
  released, whether the learner's own records have been removed with `--remove-endpoint`, and
  whether each stack has been destroyed. Any step not yet done is recorded as pending, with
  `COURSE.md`, *When you are finished* as the reference, because the number keeps billing daily
  until it is released.

## Optional deeper paths

- Set `AgentAvailabilityTimer` on the routing profile (`TIME_SINCE_LAST_ACTIVITY` or
  `TIME_SINCE_LAST_INBOUND`), and reason about what it changes once there is more than one agent.
- Create a second agent with a different routing profile on the same queues, with a different
  priority, and predict which agent is offered a new call. The admin guide's rule (fewest
  contacts across all channels, then longest Available) is the starting point.
- Use **Change routing priority / age** in the voice flow for gold callers, and work out how it
  combines with the routing profile's priorities. Note that the block's change takes at least 60
  seconds to apply to a contact already in queue.
- Look at **workload type concurrency** for email, which splits an agent's email capacity by type
  of work, and at **manual assignment**, where agents pick emails from a worklist instead of
  being offered them.
- Compare `UpdateRoutingProfileConcurrency` and `UpdateRoutingProfileQueues` with redeploying the
  stack, and say why this course keeps the profile in code anyway.
