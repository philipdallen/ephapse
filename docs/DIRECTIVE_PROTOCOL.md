# DIRECTIVE_PROTOCOL — version v0.1-pilot

> Pilot copy. Adopted by DEC-041 on 2026-09-30 for the ephapse pilot only. The body below is the proposal text saved byte for byte (sha256 `b41df84f82ed362d11bb27079a58c39660be29256ecc312c61f2f1a02db4dbce`). Ephapse-specific deviations live in the `## ephapse notes` section at the end, never in the body.

# Directive-first tasks and bake-offs

Addendum to `docs/MULTI_AGENT_WORKFLOW.md`. Adds three things: (1) every task
traces back to a logged decision that exists before the task does, (2) a
consideration step so a directive cannot become a decision without research
and an explicit ratification, and (3) an opt-in competitive mode where several
agents do the same task and only the winner merges. Everything not mentioned here (run-ids, atomic claims, blockers,
sweeps, gates, 30-minute cap, `<!-- oh-agent -->` marker) is unchanged.

Terms: **Orchestrator** is the top-level agent that turns the human's direction
into decisions and tasks. **Worker** is any agent that claims a task.

## 1. Directive-first rule

No task issue may be filed until the decision that justifies it is in
`docs/decisions/LOG.md` on `origin/main`.

Order of operations, every time:

1. The human gives direction (chat, issue comment, blocker answer).
2. The Orchestrator classifies it (section 1a) and, unless it is Tier 0,
   appends a **`Proposed`** DEC quoting the direction and pushes it to `main`
   (the ratification timestamp is checked against this commit). No task is
   filed yet.
3. Consideration runs per tier (section 1a). The human ratifies in a comment.
4. The Orchestrator flips the DEC to `Active` in a second commit, pushes it
   to `main`, then files task issues. Each issue carries `Directive: DEC-NNN` in its body.
5. Workers claim, decompose, and implement (sections 2 to 4).

The timestamp order (DEC commit before issue creation before implementation
commits) is the evidence that direction came first. Do not backdate, batch, or
write the DEC after the fact. If a DEC is written late, say so in the entry
(`Logged-late: true`, reason). Late entries are allowed, silent ones are not.

### DEC entry format (extends the existing one)

```
### DEC-0XX

**Date:** YYYY-MM-DD
**Status:** Proposed | Active | Rejected | Superseded
**Tier:** 1 | 2   (section 1a)
**Scope:** ...
**Origin:** human | agent-proposed | blocker-resolution
**Directive (verbatim):** "<the human's words, quoted, with link to the message or comment>"
**Decision:** ...
**Rationale:** ...
**Consideration:** link to the memo (`docs/decisions/considerations/DEC-NNN.md`)
**Ratified:** link to the human's `RATIFY DEC-NNN` comment, with its timestamp
**Spawns:** #NN, #NN   (filled in as issues are filed)
**Acceptance:** observable end state that would tell us the decision worked
```

Rules:

- **Origin is honest.** If the human said it, `human` and quote it. If the
  Orchestrator inferred it, `agent-proposed` and Status stays `Proposed`. No
  task may be filed against a `Proposed` DEC except a research task whose
  deliverable is asking the human to ratify it. The human ratifies by comment,
  the Orchestrator then flips Status to `Active` and records the ratifying
  comment link.
- **Verbatim directive is mandatory for `human` origin.** A paraphrase is the
  Orchestrator's summary, not the human's direction, and is weak evidence.
- **No silent direction changes.** A scope cut, retired approach, added gate, or
  invalidated result is a DEC. Superseding an old DEC requires a new entry that
  names it, never an edit to the old one (the log stays append-only).
- **Agents may not make semantic decisions.** Existing rule stands: notation
  forks are the agent's call, semantic forks go to the human. A worker who needs
  a semantic decision files a blocker (section 3), it does not write a DEC.

### Commit trailers

Every implementation commit carries:

```
Directive: DEC-NNN
Refs: #NN
Run-id: <run-id>
```

Bake-off commits also carry `Bakeoff: #PARENT/<slot>` (section 4).

### Enforcement (spec, to be built as `tooling/gates/directive_scan.py`)

Advisory prose is exactly what the audit flagged, so this gets a scanner. It
fails (exit 1) when:

- a `status:available` or `status:claimed` issue has no `Directive: DEC-NNN`;
- the cited DEC does not exist in `LOG.md` on `origin/main`;
- the cited DEC is `Proposed` and the issue is not a ratification task;
- the DEC's commit date is later than the issue's creation time and the DEC
  lacks `Logged-late: true`;
- a commit on `main` has no `Directive:` trailer (warning for the first two
  weeks, violation after).

Add it to the start-of-session sweep next to `pass_scan.py` (§Claiming step 1a).
A queue with directive violations is not claimable.

## 1a. Consideration step

The purpose is to stop a half-formed idea from becoming a decision that
dozens of tasks inherit. The process scales with how expensive the decision
is to undo, so routine work does not pay for it.

### Tiers (the Orchestrator assigns, the human may override up)

| Tier | What it is | Process |
|---|---|---|
| 0 | New task clearly inside an existing Active DEC's scope and Acceptance | No new DEC. File the task under the existing `Directive:`. |
| 1 | New direction that is cheap to reverse (new task family, new experiment, a new non-gating tool) | Consideration memo, then ratify. No waiting period. |
| 2 | Hard to reverse or load-bearing: adds, removes, or changes a gate; retires an approach; cuts scope; invalidates or reclassifies a result; changes a hypothesis, rubric, or statement; touches cross-repo contracts; opens a bake-off with more than 2 slots | Consideration memo, independent challenge, ratify after a waiting period |

When unsure between tiers, pick the higher one. Misclassifying down is the
failure this step exists to prevent, so the scanner checks tier against the
keywords above and the Orchestrator must justify any Tier 0 or 1 that matches.

### The consideration memo

A research task, filed under the `Proposed` DEC, sized like any other task.
Deliverable is `docs/decisions/considerations/DEC-NNN.md` with:

1. **Direction restated** in one sentence, next to the verbatim quote, so
   misreadings surface before work starts.
2. **Why now.** What triggered this and what happens if we wait a week.
3. **Conflicts.** Every existing DEC, open issue, blocker, and hypothesis-grid
   row this touches or contradicts, found by searching `LOG.md`, the queue,
   and `git log origin/main`. "None found" must list the searches run.
4. **Options.** At least three: the directive as stated, a narrower version,
   and do nothing. Each with cost (runs, human attention), what it makes
   easier, what it makes harder.
5. **Reversibility.** What undoing it costs and what would be stranded.
6. **Falsifier.** The observable result that would tell us in a few weeks the
   decision was wrong. This becomes the DEC's `Acceptance`.
7. **Evidence.** Claims about the repo cite file, commit SHA, or issue number
   from raw artifacts, not README prose or another agent's summary. Anything
   unchecked is marked `unverified`.
8. **Recommendation** and the single open question for the human, if any, as
   a `NEEDS:` line.

The memo recommends. It does not decide, and it does not file the tasks.

### Independent challenge (Tier 2 only)

A second run that did not write the memo files `docs/decisions/considerations/
DEC-NNN.challenge.md`. Its only job is to argue against the recommendation:
the strongest case for a different option, conflicts the memo missed, and the
cheapest experiment that would settle the question instead of deciding it. It
must re-run the memo's searches itself. A challenge that only agrees is
treated as missing.

### Ratification

- The human ratifies with a comment containing exactly `RATIFY DEC-NNN`, or
  rejects with `REJECT DEC-NNN` and a reason. Silence is not ratification, and
  neither is a thumbs-up reaction or a chat message elsewhere.
- Ratification must be **later than the memo's commit** (and the challenge's,
  for Tier 2). This is what proves the memo was available before the decision.
- **Tier 2 waiting period: 24 hours** between the memo (and challenge) landing
  and the earliest valid `RATIFY`. The Orchestrator does not remind or chase.
  A decision that cannot survive a night's sleep was not urgent.
- **Override:** the human may ratify early with `RATIFY DEC-NNN URGENT: <reason>`.
  It is allowed, and the reason is copied into the DEC. The scanner counts
  overrides so the pattern is visible in the end-of-session report.
- **Amending while pending.** If the human changes the direction after the memo
  is written, the memo is stale. The Orchestrator files a new `Proposed` DEC
  that supersedes the old one, and the clock restarts.
- **Rejected** DECs stay in the log with status `Rejected` and the reason, so
  the same idea is not reconsidered from scratch next month.

### What the Orchestrator may not do

- File any task under a `Proposed` DEC, other than the memo and challenge.
- Start the memo for a direction it judges unclear. Ask a `NEEDS:` line first.
- Expand scope in the memo. Additional ideas found during research go in a
  `Not in my lane` line, or a separate `Proposed` DEC of their own.

### Scanner additions (`directive_scan.py`)

Extends section 1's checks. Fails when:

- an `Active` Tier 1 or 2 DEC has no consideration memo, or the memo lacks any
  of the eight required headings;
- a Tier 2 DEC has no challenge file;
- the `RATIFY` comment is missing, is not by the human account, or predates the
  memo or challenge;
- a Tier 2 ratification is under 24 hours after the memo without `URGENT:`;
- a DEC matches Tier 2 keywords but is recorded as Tier 0 or 1;
- any task other than the memo or challenge cites a `Proposed` DEC.

## 2. Pickup and decomposition

Workers pick up work through the normal claim protocol. One addition: a task
may be **decomposed** instead of implemented.

- Decomposing is a legitimate run. The worker claims the parent, files child
  issues, releases the parent, and posts a `DECOMPOSED` comment listing the
  children. That is a complete, successful run.
- Children inherit the parent's `Directive: DEC-NNN`. They do not get a new DEC.
- Children use native `Blocked by` relationships and obey the existing sizing
  rule (20 minutes or less of work) and the multi-pass rules.
- **Depth cap: 2.** A child may decompose once more. A grandchild may not.
  Anything that needs a third level goes to the human as a blocker, because
  the plan is underspecified.
- **Decomposition may not widen scope.** The union of the children must equal
  the parent's Definition of Done. Work the worker thinks is also needed but
  is outside the DoD becomes a blocker or a `Not in my lane` line, not a child.
- The decomposing worker checks for duplicates before filing (existing
  search, file, search again rule).

## 3. Blockers as human tasks

Existing blocker mechanics stay. This section tightens the loop so every
human answer becomes a logged decision.

1. Worker hits a semantic fork, writes `blockers/open_*.md`, labels the issue
   `status:blocked-needs-input`, opens the comment with a `NEEDS:` line, and
   moves on.
2. The blocker is itself a task in the human's queue: label it `needs:human`
   so `needs-audit.sh` lists it.
3. The human answers on the issue.
4. **The Orchestrator, not the worker, records the answer** as a new DEC with
   `Origin: blocker-resolution`, the human's answer quoted verbatim, and the
   blocker issue linked. It pushes the DEC, then the blocked task returns to
   `status:available` with `Directive:` updated to the new DEC.
5. The blocker file is renamed `closed_*` as today.

A blocker resolved without a DEC is a protocol violation, because the
decision would live only in a comment thread. A blocker answer that merely
resolves an ambiguity inside an existing DEC's scope is Tier 0 and is logged
as described above. One that changes direction is classified under section 1a
like any other new directive.

## 4. Bake-offs (competitive duplicate work)

Normal rule: never push a second copy of the same work. A bake-off is the one
sanctioned exception, and it is opt-in per task.

### When to use one

Use when the task has a real design choice and more than one plausible answer
(statement renderings, gate design, schema shape, experiment harness design,
prompt or pipeline structure). Do not use for mechanical work with one correct
output. Bake-offs multiply cost by N and each slot still has to fit in a run,
so the Orchestrator decides per task and records why in the DEC.

### Setup (Orchestrator, before any slot opens)

The parent issue is labeled `bakeoff` and contains, **frozen before slots open**:

- **Slots:** N of 2 or 3. More than 3 needs a DEC explaining why.
- **Lens per slot:** a distinct named approach (existing slot-diversity
  discipline). Same model with a different seed is not a different entry, so
  the lens must change the approach, not the randomness.
- **Rubric:** ordered, mostly machine-checkable criteria, each with a command
  or an observable threshold. Example order: (1) all gates pass, (2) tests pass
  and coverage meets the spec, (3) measured metric (runtime, sorry count,
  proof length, conformance count), (4) simplicity (lines, dependencies),
  (5) reviewability. Earlier criteria dominate later ones.
- **Tie-break:** what happens if the rubric does not separate the entries
  (default: escalate to the human as a blocker, never a coin flip).

The slots, lenses, and rubric are drafted in the consideration memo and fixed
by the human's `RATIFY`. The rubric is immutable once any slot is claimed. Changing it after seeing
entries means cancelling the bake-off and filing a new one, with a DEC.

### Slots

- One issue per slot, `Blocked by` nothing, labeled `status:available`, each
  carrying the parent's `Directive:`, its lens, and `Bakeoff: #PARENT/<slot>`.
- Claimed with the normal atomic claim. One claim per agent still applies, and
  **one agent may not hold two slots of the same bake-off**.
- **Isolation:** a worker must not read any sibling slot's branch, files, or
  comments until its own entry is submitted. A violation is recorded in the
  slot comment and disqualifies the entry.
- **Branches, not main.** Each slot works on `bakeoff/<parent>/<slot>` and
  pushes constantly (existing push rule). Slots do not commit to `main`. This
  is the one exception to the commit-to-main rule.
- Submitting = slot issue gets a `SUBMITTED` comment with the head SHA and the
  rubric commands run on that SHA with their output. Then `status:done` on the
  slot means "submitted", not "merged".

### Judging

Start when all slots are submitted or the parent's deadline (default 24 hours)
passes. A missing entry is a forfeit, not a reason to wait.

1. **Machine pass.** A judge runs every rubric command against every submitted
   SHA and records the results in a scorecard table on the parent issue.
   Raw command output, not summaries.
2. **Judge independence.** The judge is a run that submitted no entry in this
   bake-off. It does not edit any entry. It may not re-run an entry's own
   reported numbers as a substitute for its own runs.
3. **Decision.** Apply the rubric in order. If it separates the entries, that is
   the winner. If it does not, follow the pre-registered tie-break.
4. **Semantic disagreement.** If entries differ in what they claim (for example
   two statement renderings that are not equivalent), that is not something to
   score. It goes to the human as a review point, as the rendering-campaign
   protocol already does.
5. **All entries equivalent and all pass** is a valid outcome and a measured
   result. Pick the simpler one per rubric criterion 4 and record that the
   task was unambiguous under these lenses.

### Merging the winner

- The **Orchestrator** writes a DEC recording the result: winner, scorecard
  link, losing entries, and the reason the rubric picked it. `Origin:
  agent-proposed` with the rubric as the pre-ratified authority, unless the
  tie-break went to the human, then `Origin: human`.
- Merge only the winner to `main`, as a squash or cherry-pick on top of current
  `main` (rebase first), with trailers `Directive:`, `Bakeoff: #PARENT/<slot>`,
  `Won-over: <slot>, <slot>`.
- **Do not delete losing branches.** Tag each `bakeoff-lost/<parent>/<slot>`
  at its head SHA and link it from the scorecard. The rejected entries are the
  record of what was considered and why it lost.
- Do not merge parts of losers into the winner in the same commit. If a loser
  has a piece worth keeping, file a follow-up task citing it. This keeps the
  winner's provenance clean.
- Only the winner's slot gets a `Tests:` follow-up. Dependents of the parent
  unblock only after the winner is merged and pushed.
- Parent closes `status:done` with the done comment containing the scorecard
  and the merge SHA.

### Sweep additions

- A `bakeoff` parent with all slots submitted and no scorecard after 24 hours
  is stale: the sweep starts judging or escalates.
- A `bakeoff-lost/*` tag with no scorecard link is a violation.
- A slot branch with commits to `main` is a violation (isolation and merge
  rules).

## 5. Edits required to existing text

These existing rules conflict with or need to reference the above. Amend when
merging:

| Existing rule | Change |
|---|---|
| Duplicate-work rule (DEC-026, PleaNP §Claiming step 5) | Add: "except inside a sanctioned bake-off (section 4), where duplicate entries live on slot branches and only the judged winner merges." |
| Recent-activity guard (step 1) | Add: slots of one bake-off are not duplicates of each other. The guard still applies between bake-offs and ordinary tasks. |
| "Commit directly to `main`" (step 5) | Add the slot-branch exception. |
| Task definition | Add `Directive: DEC-NNN` as a required field. Add `Bakeoff` block as an optional one. |
| Sweep (steps 1 to 1c) | Add `directive_scan.py` and the bake-off sweep checks. |
| Blockers | Add `needs:human` label and the step 4 rule that the Orchestrator logs the resolution as a DEC. |
| Task states (labels) | Add `bakeoff`, `needs:human`. |
| End-of-session report | Add: DECs proposed, ratified, rejected, and `URGENT` overrides used; DECs written (with origin), tasks decomposed (with children), bake-offs opened, judged, merged, or escalated. |
| Decision log status vocabulary | Add `Proposed` and `Rejected` to the `Active`/`Superseded` set. Create `docs/decisions/considerations/`. |
| Start-of-session sweep | Add: list `Proposed` DECs older than 7 days with no memo or no ratification, and report them. Do not act on them. |
| `docs/decisions/LOG.md` header | Replace the format line with the extended entry format in section 1. |

## 6. What this protocol does not do

- It does not prove a human authored a direction. It makes the human's
  words and the ordering visible and checkable. A commit trailer or a DEC
  written by an agent is still a self-report, which is why the verbatim quote,
  the link to the original message, and the DEC-before-issue ordering are
  required.
- It does not make the human think. It guarantees a written memo, a challenge
  for the costly cases, and a delay exist before a direction binds the queue.
  A human who reads neither and types `RATIFY` still passes the scanner. The
  override count and the `Rejected` log are the only signals of how often that
  happens.
- It does not fix the agents-share-one-model problem. Lenses help, but two
  entries from the same model can still share blind spots. A bake-off that
  unanimously agrees is evidence of unambiguity under these lenses, not of
  correctness.


## ephapse notes

Deviations, confirmed against this repo rather than copied from the proposal:

- **Ratification was out of band.** DEC-041 was ratified by the owner in chat
  on 2026-09-30 ("Complete the new process"), not by an in-band `RATIFY DEC-041`
  comment. Every comment in this repo is posted by the single shared account
  `philipdallen`, so a chat instruction and a comment are indistinguishable at
  the API and a `RATIFY` comment would have been authored by the agent, not the
  human. The 24-hour floor (2026-10-01T12:43:30Z) was waived by the owner, not
  met. This is the weakness section 1a names, and it is recorded rather than
  hidden.

- **Branch policy.** DEC-001 still names `dev`; `AGENTS.md` records the rename
  to `main` on 2026-09-22. The protocol is applied against `main`. The bake-off
  slot branch is a named exception to the commit-to-`main` rule in
  `docs/MULTI_AGENT_WORKFLOW.md` § 5, not a second branch policy.

- **Scanner default.** `directive_scan.py` ships **warn-only**; `--strict` is
  opt-in. The Phase-2 brief asked for warn-only, and a gate that fails the queue
  it governs before its own fixtures prove it can fail would be the exact
  artifact this repo's gate discipline exists to prevent.

- **Grandfather cutoff.** Every issue up to and including **#88** is grandfathered
  (the highest issue number recorded in Phase 0). The `Directive:` field is
  required from #89 onward. Consideration issues #89 and #90 are themselves
  covered by the grandfather rule.

- **`needs:human` is created but not yet enforced.** The label is created in this
  repo; wiring it to a check is part of the pilot, not this change.

- **`pass_scan.py` does not exist here** and no gate tool has an offline
  `--json-file` mode, so `directive_scan.py` follows the `check_docs_coherence.py`
  pattern: a standalone entry point plus `run_all.py` registration, no
  `--json-file` flag. This is the challenge's **C7** — the frozen body still says
  "next to `pass_scan.py`"; the body is ratified and cannot be edited, so the
  dead anchor is corrected here and the wiring lands next to the real
  start-of-session tools (`claim.py status`, `audit_claims.py`).

- **Grandfather clause (the challenge's C8).** The scanner would otherwise fail
  the whole live queue on its first run. Every issue up to and including **#88**
  is grandfathered, which is why `GRANDFATHER_MAX` exists in the code and not
  only in prose. The scanner is warn-only by default; `--strict` is opt-in.

- **The proposal's DEC-026 citation is wrong (the challenge's C9).** Proposal §5
  attributes the duplicate-work rule to DEC-026; the rule actually lives in
  `docs/MULTI_AGENT_WORKFLOW.md` § 5 ("Never push a second copy") and the
  recorded instance is DEC-028. The body is frozen, so the amendment in § 5 of
  the workflow cites the real location, not DEC-026.
