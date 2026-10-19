# Red-team verdict — the rung-3 null is adversarially replicated

> **Issue:** #154 (step 4 of the #150 split). **Run:** `20261019-1602-3upj`.
> **Date:** 2026-10-19. **Directive:** DEC-033.
> **Basis:** `docs/reference/REDTEAM_PREREGISTRATION.md` (the frozen grid, §1–§7),
> the step-2 reproduction (`experiments/2026-10-19-rung3-redteam-step2-results.json`),
> the step-3 grid (`experiments/2026-10-19-rung3-redteam-step3-results.json`), and
> the #145 real arm (`findings.jsonl` line 6).

> **What this document is.** The written red-team verdict, in #145's form, plus
> the bias-audit section #150 acceptance criterion 3 requires. It records an
> **observation about an instrument**, not a mathematical result. The rung-3 null
> is a null *of the SAE instrument at `gemma-2-2b`*; nothing here is a claim about
> structure in the world.

## 1. What was asked

`#150` commissioned an adversarial replication of the rung-3 null (#145) because
that null's validation was entirely common-mode: same apparatus, same agent
family, same night, self-graded gates, and a pre-registration written and
executed by the same hands. The red team was to reimplement from the
pre-registration alone (independence, §4), vary a frozen grid of axes
(§1), report **every** cell with no file-drawer (§0), and state a verdict in the
same form as #145 plus a bias audit. The null is upgraded only if the
pre-registration held, every cell was reported, and there were zero survivors
(§5).

## 2. Verdict

**The rung-3 null survives the red team. Zero survivors in every pre-registered
cell.** Under the decision rule frozen at §5 — the null survives only if
**every** cell reports `n_survivors = 0` under its own family-wise cutoff — the
null is not re-opened.

**Survivor counts under both firing rules** (the #145 form):

| Firing rule | Cells run | Survivors | best-z range |
|---|---|---|---|
| `gt0` (primary) | 37 | **0** | 3.543 – 5.754 |
| `pct95` (secondary) | 24 | **0** | 3.140 – 5.330 |

**Frozen reference cell** (`g-11-5-0.5-gt0-12`, the cell the red team tries to
break) — reproduced by the independent implementation:

| | best_z | cutoff | n_survivors |
|---|---|---|---|
| #145 (frozen config) | 3.695 | 4.664 | 0 |
| red team (reference cell) | 3.695 | 4.660 | 0 |

**Grid coverage** (§0: no cell omitted, including `not_runnable`):

| | Count |
|---|---|
| Pre-registered cells | 73 |
| Cells run and reported | 61 |
| Cells reported `not_runnable` (empty family) | 12 |
| Cells with ≥1 survivor | **0** |

The 12 `not_runnable` cells are the `pct95` cells at `MIN_SUPPORT = 10` on the
layer-13 hook, where the band floor `lo = 10/120 = 0.0833` excludes every feature
under that rule. They are reported with that reason, not dropped (§0).

## 3. Gates output

```
python3 tooling/gates/run_all.py
24/24 gates PASS
EXIT=0
```

## 4. Findings record

`findings.jsonl` carries the new record (line 7, `issue: 154`,
`kind: redteam_replication`, `verdict: null`); `findings.highwater` was raised
`6 → 7` in the same change, so the append-only gate (G-E6) sees a consistent log.

## 5. Bias audit — what the red team changed vs kept, and where results diverged

The audit was **pre-registered** (`REDTEAM_PREREGISTRATION.md` §7) *before* any
cell ran, so the red team could not choose its axes after seeing results.

| #145 choice | Red-team action | Outcome |
|---|---|---|
| Band support floor `5` | **Changed** (axis A: `3`, `5`, `10`) | 0 survivors at every value |
| Band cap `0.5` | **Changed** (axis B: `0.5`, `0.7`) | 0 survivors at both values |
| Firing rule `gt0` only | **Changed** (axis C: `gt0`, `pct95`) | 0 survivors under **both** rules |
| Seed `11` | **Changed** (axis D: `3`, `17`, `29`) | 0 survivors at every seed |
| Hook `blocks.12` | **Kept primary; layer 13 attempted** (axis E) | layer-13 SAE loaded and ran; 0 survivors at both hooks |
| Corpus construction (DEC-011) | **Kept** | protocol invariant, not a variation |
| Standardized statistic + family-wise max correction | **Kept** | the DEC-027 fix, not a knob |
| `N_PERM = 400` | **Kept** | cutoff construction unchanged |
| Positive-control order (constructibility first) | **Kept** | DEC-019 |

**Where results diverged from #145.** In one place, and it is not in the verdict:
the frozen reference cell reproduces `best_z = 3.695` to three decimals, but the
independent implementation's family-wise cutoff is `4.660` against #145's `4.664`
— a 0.004 difference attributable to the permutation RNG in the second
implementation, not to any varied axis. The survivor count is identical (`0`), and
`best_z` sits ~0.96 below the cutoff, so the difference does not approach the
decision boundary. No varied axis produced a survivor, so there is no
axis-attributable divergence to report.

**Independence (§4).** Steps 2–3 were reimplemented from
`REDTEAM_PREREGISTRATION.md` + `RUNG3_PREREGISTRATION.md` alone; they do not read
or adapt `experiments/2026-10-19-rung3-real-arm.py`, the #143–#145 probe, or any
#143–#145 results JSON. The one environment-forced deviation is recorded in the
step-2 done comment: TransformerLens 3.9.0 cannot load `Gemma2ForCausalLM`, so the
hook tensor is read from the plain `transformers` forward pass as
`hidden_states[13]` (residual after block 12), masked to real tokens — the same
tensor the hook exposes.

## 6. Upgrade determination

`#150` acceptance criterion 5 upgrades the rung-3 null from "internally validated"
to "adversarially replicated" only if:

| Condition | Held? |
|---|---|
| Pre-registration committed before any cell ran (§9 falsifier 1) | **Yes** — the grid is frozen at the commit that adds `REDTEAM_PREREGISTRATION.md` |
| Every cell reported, none omitted (§9 falsifier 2) | **Yes** — 61 runnable + 12 `not_runnable`, all 73 listed |
| Zero survivors in every cell (§5) | **Yes** — 0 in all 61 runnable cells |
| Independence constraint (§4) honoured (§9 falsifier 3) | **Yes** — reimplemented from the pre-registration alone |

**All four hold. The rung-3 null is upgraded from "internally validated" to
"adversarially replicated".** Any survivor would have re-opened the question; none
was found.

## 7. Caveats (stated, not retired)

- **A null here is a null of the SAE instrument at `gemma-2-2b`.** The comparator
  cross-cut (DEC-034 apparatus, landed at 70M in #37) is untested at rung-3 scale,
  so the **scale explanation is not retired** — the red team tested the null's
  internal robustness, not the instrument-vs-scale question.
- **Feature absorption** is the primary alternative explanation for a null and
  may be structural to the sparsity objective: a null may reflect SAE
  representational limits rather than an absence of structure (PRIOR_ART §4).
- The adversarial replication shares the step-2 encoder with the step-3 grid
  (same arm), so the two steps are not independent of each other — only
  independent of the #143–#145 chain.

## Reproducing the basis

- `docs/reference/REDTEAM_PREREGISTRATION.md` — the frozen grid, decision rule,
  and pre-registered bias audit.
- `experiments/2026-10-19-rung3-redteam-step2-results.json` — the reference-cell
  reproduction.
- `experiments/2026-10-19-rung3-redteam-step3-results.json` — all 73 cells.
- `findings.jsonl` line 7 — the verdict record, run `20261019-1602-3upj`.
- `docs/decisions/LOG.md` — DEC-033 (rung ladder), DEC-019 (constructibility),
  DEC-027 (standardized statistic), DEC-016 (family-wise max correction),
  DEC-034 (comparator cross-cut).
- #150 (the commission) · #151 (pre-registration) · #152/#153 (execution) ·
  #145 (the null under replication).
