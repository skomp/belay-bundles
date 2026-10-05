---
id: 00-instance-and-first-agent
title: Instance and first agent
design_refs: [instance-choices, stack-split]
validators: [cdk-synth, pytest, instance-live]
---

## Purpose

Stand up an Amazon Connect instance from code and get a human — you — logged into it as an agent.

Nothing else in this course can happen until there is an instance to put it in and an agent
to receive what it routes. The pressure in this lesson is that two of the instance's choices,
its **identity mode** and its **alias**, are fixed at birth, and the alias becomes your email
domain in the next lesson. So you decide them once, deliberately, and you put the instance in
a stack that you never have to destroy. By the end, the long-lived stack `ConnectCore` holds
the instance, the churning stack `ConnectRouting` holds one agent user, and you have logged in
to the agent's Contact Control Panel and set yourself **Available**. Nothing is routed to you
yet; that is lesson `01-first-email-contact`.

## Prerequisites

This is the first lesson. You need what `COURSE.md` lists under *What this course assumes you
have*: AWS fluency, CDK in Python at the level of a small deployed app, Node.js for the CDK
CLI, and an AWS account you may create billable resources in, with credentials for one account.
The runner checks Python, Node.js and your AWS credentials before this lesson starts
(`toolchain-present`); the CDK CLI and the Python packages are installed in this lesson, so the
check reports them as "not yet" rather than failing.

The supplied skeleton is already in your workspace: `app.py` creates the two stacks,
`contact_centre/core_stack.py` (`CoreStack`, deployed as `ConnectCore`) and
`contact_centre/routing_stack.py` (`RoutingStack`, deployed as `ConnectRouting`, which receives
the core stack as `core=`) are empty classes for you to fill, and `tests/conftest.py`
synthesizes both stacks into templates your tests assert against. `README.md` describes the
layout.

## Learning objectives

- Explain what an Amazon Connect **instance** is — the container for users, queues, flows,
  phone numbers, email addresses and every contact — and which of its properties can never
  change after creation
- Choose an **identity management type** and an **alias** deliberately, and say why this course
  uses `CONNECT_MANAGED` and `<learner-prefix>-tutorail-cc` (`#instance-choices`)
- Explain the instance attributes `InboundCalls` and `OutboundCalls`, and why both must be set
- Distinguish a **security profile** (what a user may *do* in Connect) from a **routing
  profile** (which contacts a user is *offered*), and predict which one decides what an agent
  receives
- Place the instance in the long-lived stack and the agent user in the churning stack, and
  explain what would break if they were the other way round (`#stack-split`)
- Find the identifiers of an instance's default resources, and recognise a hard-coded,
  looked-up ARN as a temporary smell rather than a design
- Log in to the instance's admin website and to the agent's Contact Control Panel, and set an
  agent **Available**

## Theory

**A contact centre in one paragraph.** Customers reach a business over *channels* — a phone
call, an email, a chat. Each arrival becomes a **contact**: one unit of work with a start, an
end, and a record of everything that happened to it. A contact runs through a **flow**, a small
program that decides what to do with it, and is usually put in a **queue** to wait. **Agents**
are the people who take contacts out of queues and handle them. What joins agents to queues is
a **routing profile**: it says which queues an agent works, on which channels, and how many
contacts at once. You will build each of these, one lesson at a time. In this lesson you build
only the container and the first person in it.

**The instance.** An Amazon Connect instance is the container for all of it: users, queues,
hours, routing profiles, flows, phone numbers, email addresses and the contacts themselves.
Contacts and users belong to exactly one instance and never move between instances. In
CloudFormation it is `AWS::Connect::Instance`, and in CDK `CfnInstance`. Its required
properties are `IdentityManagementType` and `Attributes`; `InstanceAlias` is required for the
identity mode this course uses.

**Two choices that are permanent.** `IdentityManagementType` decides where users live:
`CONNECT_MANAGED` (users and passwords live in Connect itself), `SAML` (users sign in through
your identity provider) or `EXISTING_DIRECTORY` (an AWS Directory Service directory). The
`InstanceAlias` is a globally unique name: it appears in every URL of the instance —
the admin website and the agent's panel live under `https://<alias>.my.connect.aws/` — and,
in lesson `01-first-email-contact`, it becomes your email domain,
`<alias>.email.connect.aws`. Both properties are marked **Update requires: Replacement** in
the CloudFormation reference. A replacement of an instance is not a migration: it is a new,
empty instance with a new id, and the old one is deleted together with its users, flows,
email address and every contact record. That is why this course fixes both
(`#instance-choices`): `CONNECT_MANAGED`, because no directory or SAML provider is needed for
one agent; and the alias `<learner-prefix>-tutorail-cc`, where the prefix is something of
yours that makes it unique. The alias pattern allows letters, digits and hyphens, at most 45
characters, and it must not start with `d-`.

**Attributes.** `Attributes` toggles instance-level features. Two of them are required:
`InboundCalls` (may the instance receive phone calls) and `OutboundCalls` (may agents place
calls). You will claim a phone number and take calls in lesson `06-a-phone-line`, so inbound
calls must be on by then; whether you want outbound calls is your decision to make and
defend. Unlike the identity mode and alias, attributes update **without interruption**, so a
wrong choice here costs one deploy, not an instance. One attribute you will *not* set now is
`ContactflowLogs`: turning on flow logging is part of lesson `05-following-a-contact`, where
it is the point of the lesson. When it is on, Connect itself creates the log group
`/aws/connect/<alias>`; that group is never declared in CDK.

**Never recreated.** Amazon Connect also limits the total number of instances an account can
create *and* delete within 30 days; past the limit the account must wait 30 days before it can
create or delete another. The limit is generous for normal use, but it is one more reason the
rule in this course is absolute: when something goes wrong, you fix the instance you have. You
never destroy and recreate it to "start clean". The larger costs of a recreation are the
alias, the email domain and the contact history you lose, and the console step for email in
lesson `01-first-email-contact` that you would have to repeat.

**What a new instance already contains.** A new instance comes with defaults so that it works
before you customise anything: a queue named **BasicQueue**, a routing profile named **Basic
Routing Profile** that works it, and four security profiles — **Admin**, **Agent**,
**CallCenterManager** and **QualityAnalyst**. This course replaces the default queue and
routing profile with its own in lesson `02-hours-queues-routing-profiles`. In this lesson you
borrow them.

**Security profiles and routing profiles are different things.** This is the distinction most
newcomers get wrong, and the one this lesson exists to fix. A **security profile** is a set of
*permissions*: may this user open the Contact Control Panel, edit flows, see reports, manage
users. The **Agent** profile grants access to the Contact Control Panel and little else. A
**routing profile** decides what the user is *offered*: which queues they work, on which
channels, and how many contacts of each channel at once. An agent with the Admin security
profile and no suitable routing profile is offered nothing; an agent with the narrowest
security profile and the right routing profile is offered every contact in their queues. Each
user has exactly one routing profile and one or more security profiles.

**The agent user.** In CloudFormation a user is `AWS::Connect::User`, in CDK `CfnUser`. It
requires `InstanceArn`, `Username`, `RoutingProfileArn` and `SecurityProfileArns` (one to ten).
With `CONNECT_MANAGED` identity the user also needs a **password** — the CreateUser API
requires one for this identity mode — and Connect requires a first name, last name and email
in the identity information. `PhoneConfig` is optional; it sets things such as soft phone or
desk phone and auto-accept, which matter in the voice lessons, not here. The username may have
up to 20 characters when SAML is not in use.

**A password in a template is a secret in a file.** Whatever you put in `Password` lands in
the synthesized template under `cdk.out/`, and in CloudFormation's view of the stack. The
CloudFormation reference recommends a **dynamic reference** — a value CloudFormation resolves
from Secrets Manager at deploy time, so the template holds only a pointer. A secret generated
inside the stack does this for you. Never commit a password, and never paste one into a chat
with the tutor; if one has been exposed, change it.

**Why the user lives in the churning stack.** `#stack-split` divides the app in two.
`ConnectCore` holds what must survive: the instance now, the email address in lesson
`01-first-email-contact`, and the phone number in lesson `06-a-phone-line`. `ConnectRouting`
holds everything you will change often: the user, hours, queues, routing profiles, flows, the
Lambda. You will redeploy `ConnectRouting` dozens of times, and you may destroy and rebuild it
freely; if the instance lived there, every one of those operations would be one wrong replacement
away from deleting your contact centre. References pass in one direction only: the routing
stack reads the instance ARN from the core stack. In CDK, passing `core.<something>` into the
routing stack creates a CloudFormation export in `ConnectCore` and an import in
`ConnectRouting`. That direction is safe. The other direction would make the long-lived stack
depend on the churning one, and CloudFormation then refuses to change an export while another
stack imports it — exactly the redeploys the split exists for.

**Finding the default ARNs.** The user needs the ARNs of the Basic Routing Profile and the
Agent security profile, and those exist only after the instance does. You find them either in
the admin website (each resource's page shows its ARN or id) or with the CLI:
`aws connect list-routing-profiles` and `aws connect list-security-profiles`, both with
`--instance-id`. You then put them into the routing stack as named constants. That is a
**smell**, and you should feel it: those ARNs belong to one instance in one account, a test
cannot know whether they are right, and nothing in the code shows where they came from. You
accept it for one lesson because you do not yet own a routing profile. In lesson
`02-hours-queues-routing-profiles` the stack creates its own, and the routing-profile constant
disappears.

**Two ways in.** An instance created by CloudFormation has no administrator user. You reach the
**admin website** from the Connect console: open the instance and choose **Log in for
emergency access**, which federates you in with your AWS identity. AWS recommends the instance
URL for daily use; in this course emergency access is the honest way in, because the only user
you create is an agent. The agent's own entrance is the **Contact Control Panel (CCP)** at
`https://<alias>.my.connect.aws/ccp-v2/`, or the **agent workspace**, which hosts the CCP with
more around it, at `https://<alias>.my.connect.aws/agent-app-v2/`. The agent signs in with the
username and password you gave the user. An agent's **status** decides whether routing
considers them at all: **Offline** agents are offered nothing; **Available** agents are offered
contacts from their routing profile's queues.

**One person, two logins.** For the whole course you will be both the administrator and the
agent, and you keep those as two separate logins on purpose. The agent user has only the
**Agent** security profile, so it can take contacts and little else: it cannot open the flow
designer or use contact search, which needs the **Contact search - View** permission (the Admin
and CallCenterManager profiles have it). Admin work — drawing flows, searching contacts, reading
contact records in lesson `05-following-a-contact` — goes through **Log in for emergency access**
from the instance's **Overview** page in the Connect console. Taking contacts goes through the agent
login. You could give the agent user the Admin security profile instead and use one login for
everything. Don't: an agent should have only the permissions it needs to do its job, and having two
logins shows you every day what this lesson teaches — the permissions a user has (security profile)
are separate from the contacts they are offered (routing profile).

**`Ref` is not always an id.** On `CfnInstance`, `Ref` happens to return the instance id, but
on most Connect resources it returns something else; on a user it returns the user. Get into the
habit now: wire identifiers from the `GetAtt` attributes in each resource's *Return values*
section of the CloudFormation reference (`attr_id` and `attr_arn` on the instance), and check
that an output holds what its name says after you deploy.

## Concepts to teach

The contact centre vocabulary at the level this lesson needs — channel, contact, flow, queue,
agent, routing profile — as a map the later lessons fill in; the instance as the container for
all of it; `IdentityManagementType` and its three values, and why `CONNECT_MANAGED` here; the
alias as a globally unique name that becomes the URL and the email domain; that identity mode
and alias require **replacement**, and what replacement of an instance destroys; the instance
creation and deletion limit over 30 days, and the rule that the instance is never recreated;
the required attributes `InboundCalls` and `OutboundCalls`, and that attributes update without
interruption; `ContactflowLogs` deferred to lesson `05-following-a-contact`; the default
resources a new instance contains; **security profile versus routing profile** — permissions
versus what is offered — taught until the learner can predict which one decides; the required
properties of `CfnUser`, the password requirement under `CONNECT_MANAGED`, and keeping the
password out of the repository; `#stack-split` and the direction of cross-stack references,
including that an imported export locks the exporting stack; finding default ARNs and why
hard-coding them is a smell to remove in lesson `02-hours-queues-routing-profiles`; emergency
access to the admin website, and why one person keeps two logins (admin work through emergency
access, contacts through the agent user) as least privilege and as a daily reminder of security
profile versus routing profile; `Ref` versus `GetAtt` attributes for identifiers; the CCP and agent
workspace URLs; agent status and **Available**.

## Constraints

- You write every construct yourself: the instance, its outputs, the user, the password secret
  if you use one, and the test. The tutor explains and checks; it does not write them.
- The instance lives in `ConnectCore` (`contact_centre/core_stack.py`). The user lives in
  `ConnectRouting` (`contact_centre/routing_stack.py`). Nothing in `ConnectCore` may refer to
  anything in `ConnectRouting`.
- `IdentityManagementType` is `CONNECT_MANAGED`. The alias is `<learner-prefix>-tutorail-cc`
  (`#instance-choices`).
- `ConnectCore` publishes three `CfnOutput`s with exactly these ids, because the checks read
  them: `InstanceId` (the instance's `attr_id`), `InstanceArn` (its `attr_arn`) and
  `InstanceAlias` (the alias string). Use the `attr_*` values, not `Ref`.
- Do not set `ContactflowLogs` in this lesson.
- No account id, region or password appears as a literal in the code. The account and region
  come from your AWS configuration (`app.py` already reads them). The two looked-up default ARNs
  are the one accepted exception, as named constants, until lesson
  `02-hours-queues-routing-profiles`.
- No password is committed, printed into a file in the repository, or pasted into the
  conversation.
- The user's identity information uses a fictional name. Its email may be an address you
  control or a placeholder on a reserved domain such as `example.com`; this course puts no
  more personal data into Connect than it must.
- A test in `tests/` asserts that the core template declares an `AWS::Connect::Instance` with
  `IdentityManagementType` `CONNECT_MANAGED`.
- The agent user has the **Agent** security profile only. Admin work is done through **Log in for
  emergency access**, not by widening the agent's permissions.
- The instance is never destroyed and recreated to repair a mistake.

## Suggested progression

Start with your own setup, which the bundle cannot do for you. Install the CDK CLI (it is an
npm package and needs the Node.js you already have), create a virtualenv in the workspace,
activate it, and install the development requirements with `pip install -r
requirements-dev.txt`. Then choose your **region**. It must support the Amazon Connect email
channel, and at the time of writing those are us-east-1, us-west-2, af-south-1,
ap-northeast-2, ap-southeast-1, ap-southeast-2, ap-northeast-1, ca-central-1, eu-central-1 and
eu-west-2. Avoid af-south-1: phone numbers cannot be claimed there, and lesson
`06-a-phone-line` needs one. A learner in the EU has a reasonable choice in eu-central-1 or
eu-west-2, because the test contacts will carry your own email address and phone number. Set
the region **once, in your AWS configuration** (your profile, or `AWS_REGION`), never in the
code. Run `cdk bootstrap` for that account and region. Confirm that `cdk synth` succeeds on
the empty skeleton before you add anything, so a later failure is your code and not your
setup.

Choose your alias before you write it down. Pick the prefix, say the full alias aloud, and
check it against the rules in *Theory*. Ask yourself what in this course will carry that name
— and know that the answer includes an email address you will write to.

Write the instance in `CoreStack`: `CONNECT_MANAGED`, your alias, and the attributes. Decide
`InboundCalls` and `OutboundCalls` and be ready to say why. Add the three outputs. Before
deploying, write the test: in `tests/`, use the `core_template` fixture from
`tests/conftest.py` and assert that the template declares the instance with the identity mode
you meant. Run the tests and `cdk synth`.

Now see the permanence for yourself, without paying for it. Deploy `ConnectCore` and wait for
the instance to become usable; it takes a few minutes. Then change the alias in your code —
locally only — and run `cdk diff ConnectCore`. Read what CDK says will happen to the instance.
Put the alias back before you do anything else. Do the same thought experiment for the
identity mode. This is the instructive failure of this lesson met safely: the diff is where
you learn that a one-word edit means a new instance and the loss of everything in the old one.

Before you write the user, predict. A user needs a security profile and a routing profile.
Which of the two decides what contacts the agent will be offered? Say your answer and your
reason, then open the admin website through **Log in for emergency access** and look at both
defaults: the **Agent** security profile's permissions, and the **Basic Routing Profile**'s
channels and queues. Revise your prediction against what you saw.

Find the two default ARNs — the Basic Routing Profile and the Agent security profile — by the
CLI or the admin website, and put them in `RoutingStack` as clearly named constants with a
comment that says where they came from and that lesson `02-hours-queues-routing-profiles`
removes the routing-profile one. Write the `CfnUser` in `RoutingStack`, reading the instance ARN
from the core stack it receives. Decide how the password reaches the user without becoming a
literal in your code or a value in the repository, and how you will read it when you log in.

Then ask yourself the stack-split question out loud: what does `cdk destroy ConnectRouting`
do to your contact centre now? What would it do if you had put the instance in
`RoutingStack` beside the user? Deploy `ConnectRouting`.

Log in as the agent at the CCP URL for your alias, with the username and the password you set.
Your browser will ask for microphone access; it is for voice, which you do not need until
lesson `06-a-phone-line`. Change your status from **Offline** to **Available**. Nothing will
arrive: there is no email address and no flow yet. Leave yourself Available, or know how to
return to it.

## Completion conditions

- `ConnectCore` is deployed and declares one `AWS::Connect::Instance` with
  `IdentityManagementType` `CONNECT_MANAGED` and the alias `<learner-prefix>-tutorail-cc`, and
  publishes the outputs `InstanceId`, `InstanceArn` and `InstanceAlias`.
- `ConnectRouting` is deployed and declares the agent user, with the instance ARN taken from the
  core stack, the Agent security profile and the Basic Routing Profile. Nothing in
  `ConnectCore` refers to `ConnectRouting`.
- No password, account id or region is a literal in the code or anywhere in the repository.
- The `cdk-synth` validator passes.
- The `pytest` validator passes, and `tests/` contains a test that asserts the instance's
  identity mode from the synthesized core template.
- The `instance-live` validator passes. It reads your stack outputs and your deployed instance
  back from your AWS account; a stack that synthesizes but was never deployed does not pass.
- You have logged in to the CCP as the agent and set the status to **Available**, and you say
  so to the tutor, who records it as your statement.
- You can explain, without notes: why the alias and identity mode can never change; what
  replacing the instance would destroy; why the instance is in `ConnectCore` and the user is in
  `ConnectRouting`; and which of the security profile and the routing profile decides what an
  agent is offered, and what the other one is for.

## On completion, persist

Record in the instance's `DESIGN.md`:

- the **region** chosen, and that it is set in the AWS configuration and nowhere in the code;
- the **alias** chosen and the identity mode `CONNECT_MANAGED`, both permanent, and that the
  alias will become the email domain `<alias>.email.connect.aws`;
- the `InboundCalls` and `OutboundCalls` decisions and the reason for each;
- that the agent user lives in `ConnectRouting`, and how its password is supplied and read
  (the mechanism, never the value).

Record in `STATE.md`:

- the agent's **username** (not the password);
- the two looked-up default ARNs as **known intentional state**: hard-coded constants in
  `RoutingStack`, the routing-profile one to be removed in lesson
  `02-hours-queues-routing-profiles`;
- that `ContactflowLogs` is deliberately not yet set, for lesson `05-following-a-contact`;
- that the learner has logged in and gone Available, as their statement;
- that admin work uses **Log in for emergency access** and the agent user is for taking contacts
  only.

## Optional deeper paths

- Look up the default ARNs at deploy time instead of hard-coding them, for example with an
  `AwsCustomResource` that calls `ListRoutingProfiles`, and weigh the cost: a custom resource is
  more moving parts than one constant that disappears next lesson.
- Read the **Agent** security profile's permission list in full and decide what you would
  remove for a real agent. This is the *security profiles and least privilege* topic of the
  course's coverage.
- Compare `CONNECT_MANAGED` with `SAML`: what a contact centre that signs agents in through a
  company identity provider gains, and why this course does not build it.
- Look at the instance's other attributes in the CloudFormation reference and decide which you
  would ever want for this course and which you would not.
- Find out how to protect `ConnectCore` from an accidental `cdk destroy`, for example with
  stack termination protection, and what that changes about teardown at the end of the course.
