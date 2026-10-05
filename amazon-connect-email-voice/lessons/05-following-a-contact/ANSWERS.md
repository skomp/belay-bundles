# Answers to `tools/scenarios.py` — for the tutor only

This file stays in the lesson folder and is never supplied. Do not show it to the learner
and do not paraphrase it to them before they have named each outcome from the evidence.

The script sends three emails with `StartEmailContact` to the instance's `EmailAddress`,
without a `ContactFlowId`, so the inbound flow associated with the address runs. Against a
flow built as lessons 01–04 describe:

| Label | Sender | Subject | In `data/customers.json`? | Expected queue | Expected `route_reason` | Attribute that decided it |
|---|---|---|---|---|---|---|
| A | `ada.fairweather@example.com` | Copy of my March invoice | yes — `C-1001`, tier `gold` | priority queue | `tier-gold` | `tier` = `gold`, set by the lookup Lambda (also `customer_id` = `C-1001`, `display_name` = `Ada-Fairweather`, copied from the Lambda's `$.External` result into contact attributes by the flow) |
| B | `rowan.quill@example.com` | urgent: my order has not arrived | no | priority queue | `subject-urgent` | the email subject, segment attribute `connect:EmailSubject`, contains `urgent`; the Lambda returned an empty map, so no `customer_id` |
| C | `sam.okonkwo@example.com` | Question about your opening hours | no | course queue | `default` | none matched: the Lambda returned an empty map and the subject has no rule word |

Each contact differs from the others in exactly one decision, so the outcome does not depend
on the order of the two rules in the learner's flow. **A deliberately has a plain subject**:
which wins when a gold customer writes "urgent" is the learner's own decision in lesson 04,
and these scenarios must not depend on it. B is unknown to the table.

## Extra contacts and failed acknowledgements are expected

The senders are fictional `example.com` addresses. If the learner's flow sends the lesson 03
automatic acknowledgement with a Send message block, that reply goes to an address that does
not exist, so expect it to fail or bounce (and, in an SES sandbox account, to be refused). Each
Send message also creates an **outbound** email contact of its own, so contact search shows
more than three contacts after the script runs. The contacts to explain are the three
**inbound** ones whose ids `scenarios.py` printed with the labels A, B and C; an
acknowledgement contact is evidence that the Send message branch ran, not a fourth scenario.
`checks/live.py` searches only `INBOUND` and `API` contacts, so the acknowledgements do not
confuse it either.

## What changes the answers

- **Out of hours.** If the course queue's hours are closed when the script runs, a flow that
  checks hours first sends all three down its out-of-hours branch, and `route_reason` is
  `out-of-hours` (if the learner's flow sets it there). That is still a correct
  explanation, if the learner cites the hours check.
- **Table not loaded.** The script warns if A's sender is missing from the table; then A
  routes like C, with `route_reason` `default`.
- **Case of the subject rule.** B's subject uses lower-case `urgent`. A rule written for
  `URGENT` only, with a case-sensitive comparison, sends B to the course queue. That is an
  instructive finding, not a script error.
- **The learner's own flow differs.** The table is the expected result for the flow the
  lessons describe. If the learner's flow reached a different queue, the right answer is
  the one the evidence shows, explained from the flow log and the contact record; this
  table only tells you what to expect.

## Not verified against a live instance

- That a contact created with `StartEmailContact` has its `CustomerEndpoint` set to the
  `FromEmailAddress`, so that the Lambda receives the sender's address. The API reference
  describes `FromEmailAddress` as "the email address of the customer"; a first live run
  confirms it.
- That such a contact's subject is exposed as `connect:EmailSubject` exactly as for a
  received email.
- The contact's `InitiationMethod` (expected `API`). `checks/live.py` searches both
  `INBOUND` and `API` contacts, so either works.
