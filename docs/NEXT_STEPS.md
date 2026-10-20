# Next Steps — Ephapse handoff for orchestration

**Written:** 2026-09-19, at commit `7727d98` on `dev`; **updated** at `f0581ec`
plus the rung-3 filings (#39, #40); **§2/§3/§4/§8/§9 refreshed** 2026-10-19
against the live rung-3 chain (#143 → #144 → #145).
**Audience:** a high-level orchestrator dispatching agent sessions.
**Purpose:** what the project is, where it stands, what to work on next, and what
not to do.

Every number here was measured, not inferred. Counts drift — issues were filed
during earlier analyses, and a sibling session landed DEC-034 and #37/#38 while
this document was being revised — so re-measure before acting on a count.
`gh issue list --repo philipdallen/ephapse --state open --json number,labels` is
the cheap check; `python3 tooling/program/issue_state.py audit` covers labels and
dependencies.

---

## 1. One-paragraph orientation

Ephapse probes open-weight model internals (SAE features, activations) looking for
**cross-domain co-activation** — unrelated inputs driving the same internal
structure — as a *candidate generator* for mathematical hypotheses. It is a
sibling of Maith, not an extension: different substrate, no kernel oracle, so its
discipline comes from a two-tier automated validation layer plus process. The
product is a **candidate**, never a result; results belong to Maith's gates.

## 2. Where the method actually stands

Read [`docs/ROADMAP.md`](../ROADMAP.md) before anything else. It is the
**verdict-revision rung ladder** (adopted DEC-033), deliberately *not* PleaNP's
construction ladder, because this method has already returned a verdict.

| Rung | Question | Status |
|---|---|---|
| 0 | Can the detector detect? | **Done** — yes, with a recovering positive control |
| 1 | Is the signal more than surface form? | **Done** — weakly positive (6 survivors vs 0 on a *constructed* pair) |
| 2 | Does it fire across unrelated domains? | **Done — clean null** (DEC-027) |
| 3 | Is the null a scale artifact? | **Live — chain running.** #143 (harness) and #144 (positive control) done; #145 (real arm) claimable |
| 4 | Is a per-feature causal claim reachable? | Depends on 3 |
| 5 | Would a candidate be *interesting*? | Human step, **no falsifier** |
| 6 | Handoff to Maith | Not reached — no candidate exists |

**The single sentence that matters:** the detector works, the inputs were verified
disjoint, and the cross-domain probe found nothing at 70M. The honest reading is
*poor signal-to-noise at this scale*, not *absence of structure* — feature
absorption is the primary alternative explanation.

## 3. The next action, and it is filed

**Rung 3: re-run the rung-2 probe at larger scale.**

This is the only live rung and it is the highest-value work in the repo. It
converts "we could not see it at 70M" into "we could not see it at scale *X*",
which is either a materially stronger negative or the discovery the project
exists to find.

**It is filed as a right-sized chain of three steps**, after #142 (the original
probe issue) was superseded and split:

| Issue | What | Status |
|---|---|---|
| **#143** | Step 1 — probe harness + selectivity band at `gemma-2-2b` | **closed** `status:done` |
| **#144** | Step 2 — positive control at `gemma-2-2b` (before the real run) | **closed** `status:done` |
| **#145** | Step 3 — real cross-domain arm + findings record at `gemma-2-2b` | **claimable now** (`status:available`, `kind:experiment`) |

That sequencing is deliberate, and the split preserves it. The probe could not be
specified before its statistic was pre-registered, and the statistic could not be
chosen before the SAE and its hook were known. The two prerequisites that pinned
those parameters are now closed: **#39** (CPU feasibility for `gemma-2-2b`) and
**#40** (statistic re-derivation, pre-registered for the new SAE). Filing the
probe before them would have produced an issue whose Definition of Done could not
be written; that is why #142 was split rather than claimed whole.

**The correction that makes this actionable.** An earlier draft called rung 3
"blocked on SAE availability." **That was wrong** — queried 2026-09-19:

| Model | SAEs available |
|---|---|
| `pythia-70m-deduped` (current) | 7 |
| **`gemma-2-2b`** | **316** (`gemma-scope-2b-pt-res`); 25 in a Matryoshka residual release |
| `gpt2-small` | 12 per release, 18 releases |
| `qwen3-4b`, `gemma-3-4b-pt`, `mistral-7b`, `qwen3-8b`, `Llama-3.1-8B` | 1–9 each |

**Target: `gemma-2-2b`** — ~28× the current parameter count, ~8 GB fp32 against a
~10 GB per-run budget.

**The rule that has cost this project the most, and must be honored on rung 3:**
run the positive control *first*. Four statistics in four issues looked plausible
and could not fire — a model target, a multiplicity correction, a threshold, and a
rate cutoff. Only the control caught each. The working rule is stated in DEC-027:
**a family-wise cutoff over an unstandardized statistic is the recurring bug.**
Issue #40 existed to re-derive the statistic rather than copy it, precisely
because of this.

## 4. The work queue

### Claimable now (4 issues)

| # | Kind | What |
|---|---|---|
| **#145** | experiment | **Rung 3 step 3** — real cross-domain arm + findings record at `gemma-2-2b` (the top action, §3) |
| #148 | gap | Fold the DEC-034 comparator cross-cut into the `ROADMAP.md` rung-3 ladder |
| #149 | hygiene | Refresh the stale README status blockquote for October rung-3 |
| **#158** | experiment | **Composition emergence probe — Phase 1** (constructed set) at `pythia-70m`. Ratified DEC-043; pre-registered in `docs/reference/COMPOSITION_PREREGISTRATION.md` (this PR). Phase 2 is not filed and is gated on gates G1–G4 firing clean |

**Sequencing note:** #145 first — it is the top action and the last step of the
live rung-3 chain. #148 and #149 are docs-only and can run in parallel.

### Blocked or held (no agent should pick these up)

The remaining open issues are either `status:blocked-needs-input` — a human
judgment or a measured environment blocker — or held `on-hold` by the auditor
(#117 is a Dependabot bump PR, not claimable work):

| Group | Issues | Why |
|---|---|---|
| Needs a human decision | #17, #18, #21, #23 | Scoping questions and the irreducible human step (`kind:decision`/`kind:gap`) |
| Blocked / needs input | #36, #102, #136 | Claim-lock defect, a missing DEC reference, and shared-trio divergence |
| Held for the human (`on-hold` / `auditor:proposed`) | #45, #113–#116, #118–#120, #139, #140 | Auditor digests and tooling-drift, held by design; never claimable |

### Open defects worth prioritizing

- **#36** — the claim lock only covers sessions that use it: label/file
  divergence, and `claim.py` misreports a dead credential as a lost race.

## 5. Known breakage and hygiene debt

**Measured, not inferred:**

| Item | State |
|---|---|
| Tier-0 gates | **24 wired** (per `tooling/gates/gate_inventory.py`; do not hand-copy — recount 2026-10-18 raised 22 → 24) |
| Gate ids specified in the validation spec | 38 |
| Test suite | **154 passed, 2 skipped** (`python3 -m pytest tooling/gates/tests/ -q`, re-measured 2026-10-19) |
| The failure | none — the #25 failure (`test_real_findings_file_passes_the_registered_findings_gates`) is resolved; #25 closed `status:done` and the suite is green |
| **CI** | **Wired.** Five workflows under `.github/workflows/` (`ci.yml`, `auditor.yml`, `codeql.yml`, `hub_sweep.yml`, `proposal-issue.yml`); #13 closed `status:done` |
| Label hygiene | **G-M1 passes: 0 findings** — the #29 backfill (run `20260921-0217-a7k4`) closed the 21 findings the cache then reported |
| `kind:` coverage | Every open issue carries exactly one `kind:`; `kind:hygiene` added to the vocabulary by DEC-037 |
| Open issues | **21**, of which **3 are claimable** (`status:available`; re-measured 2026-10-19) |

**The gate-count discrepancy is resolved (#38, DEC-039; wired half #88).** Four
documents said 37, `PROGRAM_MANAGEMENT_SPEC.md` said 38, and the registry then
wired **22**. The spec's § 3 inventory enumerates **38** distinct ids (**29** tier-0
capable, **9** tier-1), so "37" was the stale figure — a hand-count that drifted
one behind the table, and the tier-1 prose was also one low. DEC-039's "11 wired"
was likewise stale (the G-C series, G-E3/E4/E5/E8, G-M3, and G-R4 landed after
it); #88 derives the wired count from `run_all.py`'s live registry so the figure
cannot re-drift. `tooling/gates/gate_inventory.py` now emits both totals from
their sources. This was exactly the docs-coherence drift **G-R4** exists to
catch, and it was caught in the window before G-R4 was wired; G-R4 is now wired
and #20 is closed `status:done`.

**Two tooling facts a session needs:**

- `python3 tooling/program/issue_state.py refresh && ... audit` — the cheap path
  for label/dependency hygiene. `refresh` reads labels *and* `blocked_by` via
  GraphQL (`gh issue list` cannot read dependencies).
- `python3 tooling/gates/run_all.py` — the authoritative gate run. A gate with no
  failing fixture reports `BROKEN` and fails, by design.
- **The `kind:` label vocabulary is a closed set** — `experiment`, `gate`,
  `repair`, `defect`, `gap`, `decision`, `protocol`, `spec`. An out-of-vocabulary
  kind makes `gh issue create` fail; this happened while filing #40
  (`kind:methodology` was rejected — a domain label used as a kind). It is now
  **single-sourced** in `tooling/program/kind_vocabulary.txt`, read by both G-M1
  and the atomic setter (DEC-035), so the two cannot disagree.
- **`kind:spec` is new** (DEC-035). Use it for work whose deliverable is a
  specification or contract a later task must satisfy — #40 and #17 are the
  examples. `gap` is for work whose *design* is unsettled; `spec` is for work
  whose design is already constrained and must be written down precisely.

## 6. What NOT to do — foreclosed, do not re-propose

**An external spec proposing a commercial "Innovation Asset Inventory" was
reviewed and rejected** (DEC-033,
[`EPHAPSE_SPECIFICATION_ASSESSMENT.md`](../reference/EPHAPSE_SPECIFICATION_ASSESSMENT.md)).
Do not reopen it, and do not dispatch work on it.

The rejections, so a dispatcher can refuse the shape rather than the exact file:

1. **No commercial framing.** The repo is *"not authorized to claim a discovery
   is novel or valid."* Anything that sells an asset asserts that.
2. **No novelty-certification filter.** The "Zero-Synapse Mandate" filters on
   *commercial precedent*, but this repo's measured problem is the opposite:
   co-activation fires *too much*. Also re-opens DEC-012, already declined.
3. **No pipeline, feasibility matrix, vault, or asset schema.** Infrastructure
   ahead of results, for an empty set. The README forbids it.
4. **No second record schema.** The program ledger (PROGRAM_MANAGEMENT_SPEC §4)
   already covers it.

Two ideas *were* rolled in (the "frictions obliterated" framing, PRIOR_ART §11)
and three postponed **with stated conditions** (vault, hotspot search,
feasibility grading). The postponed ones are conditioned on a **candidate
existing** — there are none.

**Also foreclosed by existing decisions:** no LLM in any gate or view (a
non-deterministic gate is not a gate); no promoted-findings database; no
Lean-side validation layer (that is Maith's).

## 7. How to verify any dispatched work

1. **`python3 tooling/gates/run_all.py`** — must exit 0 with every gate `PASS`.
2. **`python3 -m pytest tooling/gates/tests/ -q`** — 154 passed, 2 skipped expected
   (re-measured 2026-10-19); the #25 failure is resolved and the suite is green.
3. **Delete a fixture** — the corresponding gate must report `BROKEN`. This is the
   only way to show a gate actually works; a gate that cannot fail is not a check.
4. **For experiment work:** the positive control must run **before** the result,
   and the header must declare model, inputs, question, null, correction, issue.
5. **Claim protocol:** swap the status label and run-id in one edit, then re-fetch
   to confirm ownership. One claim per agent at a time.

## 8. If only one thing gets dispatched

**#145 — rung 3 step 3** (§3): the real cross-domain arm at `gemma-2-2b` and its
findings record. It is the last step of the live rung-3 chain — #143 (harness) and
#144 (positive control) are done — and it is the only live rung in the project.
Its two prerequisites, #39 (feasibility) and #40 (statistic), are closed.

If a second: **#148** (fold the DEC-034 comparator cross-cut into the `ROADMAP.md`
rung-3 ladder). It is docs-only and records the instrument-vs-scale verdict
revision that the landed 70M baseline already supports.

If a third: **#149** (refresh the README status blockquote). Also docs-only, and
it removes the highest-visibility staleness in the repo — a visitor currently
reads a month-old state on the front page.

---

## 9. What changed since the first version of this document

Recorded so a reader can tell what is current rather than assuming the whole
document is one vintage:

| Change | Source |
|---|---|
| Rung 3 prerequisites **filed** as #39 (feasibility) and #40 (statistic), linked `#39 → #40` | this session |
| The rung-3 probe is deliberately **not** filed yet — its DoD cannot be written before #40 pins the statistic | this session |
| **DEC-034** adopted: (1) supervised comparator baselines (#37); (2) the validation layer declared a first-class project output (#38) | sibling session |
| README gained a **"What this project produces"** section | sibling session, `7474329` |
| **#38** filed for the gate-count discrepancy (37 vs 38 vs 11 wired) | sibling session |
| A **critique response** document exists at `docs/reference/CRITIQUE_RESPONSE_2026-09-19.md` | sibling session |
| **DEC-035**: `kind:spec` added to the vocabulary; the kind list **single-sourced** in `tooling/program/kind_vocabulary.txt` (both G-M1 and the setter read it); #40 relabeled `gap` → `spec` | this session |
| **Three status-line drifts** fixed (`ROADMAP.md` said "proposal" after DEC-033 adopted it; two assessment docs still said "input to" their DECs); the class is now scoped into **#20** (G-R4) | this session |
| DEC count is now **35** (was 33) | measured |
| **§2/§3/§4/§8 refreshed** for the live rung-3 chain: #142 superseded and split into #143 → #144 → #145; #143/#144 closed `status:done`, #145 claimable; prerequisites #39/#40 closed | this session (run `20261019-0241-qxzi`) |

**One consequence for the ladder.** DEC-034's comparator baselines are a change to
the *apparatus*, not a rung. They cut across rungs 1–3: a probe that detects a
paraphrase-invariant bridge the SAE misses would move the bottleneck from model
scale to *instrument*, which is a different verdict-revision than rung 3 tests.
The roadmap has not yet been updated to record that cross-cut — #37 has since
landed (the 70M baseline is both-miss), and folding it into the `ROADMAP.md`
rung-3 ladder is filed as **#148**.

---

## Appendix — where the authoritative documents live

| Question | Document |
|---|---|
| Where does the method stand, and what would revise it? | `docs/ROADMAP.md` |
| What are the rules for claims and gates? | `docs/reference/TEST_VALIDATION_SPEC.md` |
| How is work tracked? | `docs/reference/PROGRAM_MANAGEMENT_SPEC.md` |
| How do agents claim and finish work? | `docs/MULTI_AGENT_WORKFLOW.md` |
| What is the literature position? | `docs/reference/PRIOR_ART.md` |
| What was decided, and why? | `docs/decisions/LOG.md` (DEC-001 … DEC-034) |
| What has been measured? | `experiments/README.md`, `findings.jsonl` |
| Why was the external spec rejected? | `docs/reference/EPHAPSE_SPECIFICATION_ASSESSMENT.md` |
| What was the response to the audio critique? | `docs/reference/CRITIQUE_RESPONSE_2026-09-19.md` (DEC-034) |
