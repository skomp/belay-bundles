# tutorail-bundles

A catalogue repository. Each subfolder is one self-contained tutorAIl bundle; see
`README.md` for what a bundle is and how to add one.

## Where work is tracked

**GitHub issues in `skomp/tutorail-bundles`.** Not a `TODO.md`. Every issue Claude creates
carries the `created-by-claude` label, and issue bodies are written in ASD-STE100
Simplified Technical English.

## Where course specs go

**Inside the bundle's own subfolder, as `<bundle>/SPEC.md`.** One spec per bundle, kept
with the bundle so it travels with a fork of the course. This repository does **not** use a
shared `specs/` directory at the root.

This overrides the `tutorail-authoring` create-interview default, which writes the spec to
`specs/<bundle-id>.md` outside the bundle. That default is deliberately not followed here —
a future session should keep the spec at `<bundle>/SPEC.md` and not "correct" it back. The
one consequence to keep in mind: because the spec ships inside the bundle, the validator has
to tolerate `SPEC.md`, and learners receive it with the course. Decided 2026-09-19.

## Where course-quality audits go

The findings go in an issue here, one issue per bundle. **The full report goes in
`skomp/tutorail-authoring` under `docs/audits/`**, because that is where the rubric and the
`course-quality` skill live and the report has to be readable beside them.

- `docs/audits/2026-09-12-course-quality-first-run.md` — the first run, three courses. Its
  totals are superseded; the correction note at the top says why.
- `docs/audits/2026-09-13-course-quality-all-bundles.md` — all five bundles, with the
  per-course reports in `docs/audits/2026-09-13/`.

Audits propose and never change a bundle. Applying a proposal is the `tutorail-authoring`
skill's job, after the author agrees.

## Build a tutorial in a worktree, not in this checkout

**When you are building or changing a bundle here, work in a git worktree.** Use the
`superpowers:using-git-worktrees` skill, and prefer the harness's native worktree tool
(`EnterWorktree`, a `/worktree` command, a `--worktree` flag) over a hand-rolled
`git worktree add` — a manual worktree creates state the harness cannot see or clean up.

**This section is the declared preference the skill looks for, so do not ask for consent.**
The skill asks only when the user's instructions are silent. They are not.

A branch in this checkout is not isolation. A worktree is. Learned here on 2026-09-29,
building `cpp-png-inspector`: a second session created a branch from this session's HEAD
part-way through the work, and because branches are per-checkout, every commit made
afterwards landed on *that* branch. The result was one peer commit sandwiched between
fifteen of this session's, a feature branch stranded nine commits behind its own work, and
an untangling that needs a history rewrite in a shared checkout — which is nobody's call to
make unattended. Nothing was lost and nobody staged anyone else's files. It still cost an
afternoon's clarity, and a worktree would have cost one command.

Two consequences worth knowing before you start:

- **A worktree branches from `origin/<default-branch>` by default, so commits you have not
  pushed are invisible inside it.** This repository's sessions do not push unless asked, so
  say plainly which commits are local-only and give their absolute path in this checkout,
  or push first. An agent told to read an approved `SPEC.md` that is not there will
  improvise one.
- **The authoring toolkit refuses a dirty working tree**, by design, so that `git diff` is
  an honest record of what a script did. That is comfortable in a worktree and miserable in
  a checkout somebody else is editing.

## This session owns this repository, and hands the rest over

A session here handles **`skomp/tutorail-bundles`** — the bundles and their teaching
content. Two other repositories carry work that surfaces here and cannot be fixed here:

| Repository | What belongs to it |
|---|---|
| `skomp/tutorail-authoring` | the authoring toolkit and the `course-quality` rubric: `supplies.py`, `catalog.py`, `audit.py`, the validator, and every audit report under `docs/audits/` |
| `skomp/tutorAIl` | the runner: how a lesson is presented, how an offer is made, anything drawn on the learner's terminal |

**A failing validation, a tooling defect or a runner change gets filed in the repository
that has to fix it**, never here and never only in chat. Then check `ListAgents` for a
session holding that repository and message it: one message, each issue named with its
repo (`tutorail-authoring#11`, never a bare `#11`), what it is, and what is still pending.
If no session holds it, file anyway and say so in the report. The general form of this rule
is in the global `parallel-sessions` skill, section 4a.

Known sessions at the time of writing: `tutorail-authoring-db` holds
`skomp/tutorail-authoring`, and `tutorail-8c` holds `skomp/tutorAIl` — the plugin, the
bundle format contract, the validator, the catalogue and discovery. The authoring session
shares that checkout, so name which of your commits there are still local.

An issue with a half on each side gets **two issues that point at each other**, not one:
`skomp/tutorail-bundles#4` and `skomp/tutorAIl#23` are the worked example. Say in the
runner-side issue what the bundle supplies, and what the runner must do when the bundle
supplies nothing.

**A cross-repository discussion lives in the issue, not in the messages.** Told on
2026-09-13, for `skomp/tutorAIl#25`: post the answer on the issue, then ping the session
that owns it and ask for its update; it answers on the issue and pings back; repeat. The
ping is a doorbell and the issue is the record, so a reader who was in neither session can
follow the whole argument afterwards. Answer every ping — the turn is explicit, and a
discussion where both sides wait is indistinguishable from one that is finished.

A ruling only the author can make — for example whether a project skeleton counts as toil
(`tutorail-authoring#11`) — stays pending in writing until the author makes it. Do not
pre-empt it, and pass it to the session that owns the file it changes.

## Three toolkit traps that cost this repository time

Each was hit while building `pico-ps2-usb-adapter` on 2026-09-29, each is filed against the
repository that must fix it, and each will keep happening until it is.

**A lesson title containing `": "` produces frontmatter that is not valid YAML.**
`scripts/lesson.py add` writes the title unquoted, so
`title: Events to state: joining the two halves` breaks every standard parser. The runner's
validator does **not** catch it and reports PASS; the authoring toolkit's own `yamlite`
reader *does* reject it, so the toolkit writes a file it cannot read back. Two of this
bundle's 26 titles were affected, and `rust-automaton-db` was bitten by the same thing in
`skomp/tutorail-bundles#13`. **Quote any title containing a colon**, and after authoring a
course, parse every lesson's frontmatter with a real YAML parser rather than trusting the
validator. Filed as `tutorail-authoring#26` and `tutorAIl#53`.

**A flow collection wrapped across two lines does not parse.** The restricted YAML reader
takes `aliases: [a, b,` + newline + `c]` as a syntax error, so a long `aliases:` or
`subjects:` list must sit on one physical line however wide that gets. The failure message
names a line number and not the cause.

**`supplies.py` refuses to run on an invalid bundle, even when the declaration is the
repair.** A lesson-folder file that no `LESSON.md` names is a check 6 finding; declaring it
as a lesson-scope supply clears that finding; but the tool checks validity *before* its own
edit and refuses. The way out is the format's other remedy — have the `LESSON.md` name its
material file — and then declare it. Filed as `tutorail-authoring#28`.

## Two toolkit habits that save a renumbering

Learned building `amazon-connect-email-voice` on 2026-10-05.

**Number the spec's arc from `00`.** `lesson.py add --position` is 0-based and the toolkit
names the first lesson `00-…`, like every bundle here. A spec numbered from `01` leaves
every "lesson 05" in the spec, `COURSE.md` and `DESIGN.md` off by one, and a regex that
shifts them back misses numbers that sit before a full stop.

**Each toolkit call needs a clean tree, so commit between calls.** `lesson.py add` and
`supplies.py add` refuse a dirty working tree. Adding nine lessons or fifteen supplies is
nine or fifteen add-and-commit rounds; a small driver script that runs the command, prints
the validator line and commits only on success does it in one go and stops at the first
refusal. Declare lesson-scope supplies only after each `LESSON.md` names its material file
by its own basename (`customers.json`, not only `data/customers.json`) — check 6 matches the
name relative to the lesson folder, and `supplies.py` refuses an invalid bundle.

## A total is not a grade

A course's score is comparable **against its own lessons only**. The figure tracks how
finely a lesson's `## Suggested progression` enumerates clauses, so two bundles with
different house styles are not measured with the same ruler. Never rank the bundles by
total.

## Lesson numbers are ambiguous in `webgl-typescript-scene`

Its chapters 1 to 14 map to the files `00` to `13`, and its chapters 15 to 18 map to the
files `15` to `18`, because the old lesson 14 became the optional `minimal-gltf-loader`.
Name a lesson by its id, never by a bare number.
