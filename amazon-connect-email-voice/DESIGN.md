# Design

Durable decisions about the contact centre that later lessons depend on. This is
subject knowledge for the tutor, not learner progress. It is seeded here and the
tutor appends to it as the learner makes decisions during the course.

## Instance choices {#instance-choices}

The instance uses **`CONNECT_MANAGED`** identity: users live in Connect itself, and no
directory or SAML provider is needed.

**One region, chosen in lesson 00 and used for everything.** It must support the Amazon
Connect email channel. At general availability (November 2024) those were US East (N.
Virginia), US West (Oregon), Africa (Cape Town), Asia Pacific (Seoul, Singapore, Sydney,
Tokyo), Canada (Central), Europe (Frankfurt) and Europe (London). An EU region —
`eu-central-1` or `eu-west-2` — is a reasonable choice for a learner in the EU, because the
test contacts carry the learner's own email address and phone number. Africa (Cape Town) is a
poor choice for this course: claiming phone numbers is not supported there. The learner sets
the region once, in their AWS configuration, and every later lesson and check reads it from
there rather than from a literal.

**The instance is created once and kept.** Amazon Connect limits how many instances an
account can create and delete in 30 days, and a learner who hits the limit waits up to a
month. Destroying and recreating the instance to "start clean" is never the repair for a
mistake in this course.

**The instance alias follows one convention**, `<learner-prefix>-tutorail-cc`, because an
alias is globally unique and becomes the instance's email domain,
`<alias>.email.connect.aws`.

**The phone number is a US direct-dial (DID) number, whatever the instance's region.** An
instance can claim numbers outside its own region with no opt-in, and a US DID is claimed
self-service with no documents. Many countries are not like that: Germany, for one, can
require a local address and identity documents through an AWS Support case before a number
is issued. A learner who reaches for a local number stalls for days on paperwork that teaches
nothing about Connect. The cost of the US number, for a learner outside the US, is an
international call from their own phone for each test.

**What breaks if a lesson contradicts this:** identity mode and alias cannot change after
creation, so a wrong choice means deleting the instance and every contact in it. A region
without email stalls lesson 01 with no fix short of starting over. A lesson that assumes a
local number reintroduces the regulatory stall at lesson 06. *Resolved.*

## Stack split {#stack-split}

The CDK app has **two stacks**:

- the **long-lived stack** holds the instance, the email address and the claimed phone
  number. It is deployed rarely and never torn down mid-course.
- the **churning stack** holds the agent user, hours of operation, queues, routing profiles,
  flows, the lookup Lambda and its table. It is redeployed freely, as often as a lesson needs.

References pass one way only, from the long-lived stack to the churning one (instance ARN,
email address id, phone number id). Nothing in the long-lived stack refers to anything in the
churning stack.

**Associations live in the churning stack.** Neither `AWS::Connect::EmailAddress` nor
`AWS::Connect::PhoneNumber` has a property naming the flow it runs; the link is made by the
`AssociateFlow` API (resource type `INBOUND_EMAIL`) and the `AssociatePhoneNumberContactFlow`
API. Each association is an `AwsCustomResource` in the churning stack, because it joins a
long-lived resource to a churning flow, and only the churning side may know about both.

The stack names are fixed, because the checks find the stacks by name: **`ConnectCore`** and
**`ConnectRouting`**. Each stack publishes the identifiers the checks read as
`CfnOutput`s with fixed ids; each lesson names the outputs it adds.

**What breaks if a lesson contradicts this:** a phone number in the churning stack is
released by a replacement and cannot be reclaimed; an instance that is recreated loses
its alias, its email domain and its contact history. A reference from long-lived to churning
makes the long-lived stack depend on the one meant to churn, and CloudFormation then refuses
the very redeploys the split exists for. *Resolved.*

## Flow round trip {#flow-round-trip}

**Flows are designed in the console flow designer, exported as JSON into `flows/`, and
deployed from there by CDK.** The repository is the source of truth.

Every ARN in an exported flow — queues, the Lambda, prompts, hours — is replaced with a
**placeholder** before it is committed, and the churning stack substitutes the real value at
deploy. The placeholder is CloudFormation's own `${Name}` form — `${CourseQueueArn}`,
`${LookupFunctionArn}` — and the stack loads the file and passes it through `Fn.sub` with a
map of names to values. One flow file, one placeholder convention, applied the same way every
time.

A console edit that is not exported is overwritten by the next deploy. That is intended: the
designer is where a flow is drawn, the file is what the flow *is*.

**What breaks if a lesson contradicts this:** a flow with a hard-coded ARN deploys only into
the account it was exported from, and breaks the first time a queue is replaced. A learner
who edits in the console and then deploys loses the edit and learns to distrust the tooling.
*Resolved.*

## Lambda contract {#lambda-contract}

**One lookup Lambda serves both channels.**

- **Input:** the contact's customer endpoint from the Connect event — an email address for an
  email contact, an E.164 phone number for a call. The function normalises it in one place.
- **Output:** a flat map of string attributes — `customer_id`, `tier`, `display_name` — or an
  empty map for an unknown customer.
- **Errors raise.** The flow's error branch handles a failure; the function never returns a
  fake customer to paper over one.
- **The table** is keyed on the normalised endpoint (`endpoint`: a lower-cased email address,
  or an E.164 phone number) and holds `customer_id`, `tier` and `display_name`.
- **The result is not a contact attribute until the flow makes it one.** The block's output is
  readable straight after it as `$.External.<key>`, and is lost at the end of the flow unless a
  Set contact attributes block copies it into user-defined attributes. The flow copies all
  three; that copy is what contact search, the contact record and the checks see.
- **Values stay simple.** The Lambda documentation restricts returned values to letters,
  digits, dashes and underscores, so `display_name` carries no spaces until a live walk-through
  confirms otherwise.
- **The flow block** invokes the function synchronously with response validation
  `STRING_MAP`. A synchronous invocation times out after at most 8 seconds, so the function's
  own timeout stays below that.
- **Connect needs two grants to call it:** an `AWS::Connect::IntegrationAssociation` of type
  `LAMBDA_FUNCTION` on the instance, and a resource-based permission on the function for
  `connect.amazonaws.com`, scoped to the instance ARN. The console adds the second one for
  you; CloudFormation does not.

**What breaks if a lesson contradicts this:** lesson 07 reuses the function unchanged for
voice. A contract shaped around email in lesson 04 forces a second Lambda or a breaking change
mid-course. Connect also rejects a nested response, so a richer shape fails at run time, not
at deploy. *Resolved.*

## Deliberately unresolved {#deliberately-unresolved}

- **Custom email domain.** The course uses the instance's automatic `email.connect.aws`
  domain. Moving to a domain verified in Amazon SES is explained and never built.
- **Which rule wins when two apply.** An urgent subject from a gold customer meets both the
  lesson 03 rule and the lesson 04 rule. Both send the contact to the priority queue, but only
  one `route_reason` can be recorded. Lesson 04 asks the learner to decide the order and
  record it; nothing later depends on the answer.
- **Agent concurrency numbers.** Lesson 08 asks the learner to choose and defend the
  per-channel concurrency of the routing profile. The course does not prescribe values; the
  learner's reasoning is the point.
