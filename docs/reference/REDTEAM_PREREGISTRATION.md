# Red-team pre-registration — adversarial variation grid for the rung-3 null

**Issue:** #151 (step 1 of the #150 split).
**Date:** 2026-10-19 · **Status:** pre-registered — every axis and value below is
frozen at the commit that adds this file, **before any grid cell runs**.
**Directive:** DEC-033.

**What this document is.** A bounded, frozen variation grid for the adversarial
replication of the rung-3 null (#145). It fixes *what the red team may vary, over
which values, and how each cell is reported*. It runs nothing and measures
nothing. Steps 2-4 (#152, #153, #154) execute it.

**Authority.** Complements `RUNG3_PREREGISTRATION.md` — that document fixes the
*measurement protocol*; this one fixes the *adversarial variation space*. Where
they disagree on a protocol parameter, `RUNG3_PREREGISTRATION.md` wins and the
disagreement is a defect in this file.

**The rule this document exists to honor (DEC-005).** Freeze the method before the
run. A red team that chooses its axes after seeing results is doing the same
p-hacking it was commissioned to detect. The grid is therefore frozen here, and
**any deviation is reported as a deviation** — never a silent update.

---

## PREREG-GRID — the frozen variation grid

### 0. The quantity every cell reports

Identical to #145 and to `RUNG3_PREREGISTRATION.md` §4:

```
z_feature = (observed_coactivation_rate − perm_mean) / perm_sd
cutoff    = 95th percentile, over permutations, of max_feature(z)
survivor  = z_feature > cutoff
```

Each cell reports `best_z`, `cutoff`, `n_family`, and `n_survivors` (with the
survivor feature ids, or an explicit zero). **No cell is omitted from the report,
including the frozen reference cell and any cell that could not run.** A cell that
cannot run is reported as `not_runnable` with the reason, not dropped.

**Frozen reference (the cell the red team tries to break).** #145, frozen config:
`best_z = 3.695`, `cutoff = 4.664`, `n_survivors = 0`. The red team reproduces
this first (step 2) and reports whether its independent implementation lands on
the same numbers.

### 1. Axes, frozen values, and varied values

| Axis | Frozen (primary) | Varied values | Why this axis |
|---|---|---|---|
| A. Band lower-support floor `MIN_SUPPORT` | `5` | `3`, `10` | §2's `lo` is the smallest rate whose passage-support carries a 10 %-prevalent plant; the support floor is the one free constant in that rule. |
| B. Band upper cap `CO_CHANCE_CAP` | `0.5` | `0.7` | §2's `hi` is set by the chance co-activation the statistic collapses under; the cap is the one free constant there. |
| C. Firing rule | `gt0` (primary) | `pct95` (secondary) | §4 makes `gt0` primary and `pct95` secondary; the null must hold under **both**. |
| D. Seed | `11` (reference only) | `3`, `17`, `29` | #150 scope item 3: ≥3 seeds, distinct from #145's `SEED = 11`. |
| E. Hook | `blocks.12.hook_resid_post` | `blocks.13.hook_resid_post` **(conditional — see §3)** | §1's depth-fraction analogue; layer 13 is the exact `round(0.50 × 26)` hook, layer 12 the closest keyed one. |

**Bounded grid size.** Axes A × B × C × D at the frozen hook = `3 × 2 × 2 × 3 =
36` cells. Axis E adds at most one further hook (×36), and only if that hook is
loadable (§3). This is the complete pre-registered grid. **No other axis, value,
or interaction is added after this commit.**

**Protocol parameters that are NOT varied (kept from `RUNG3_PREREGISTRATION.md`,
because they are the protocol, not the variation):** corpus construction (120
cooking / 120 astronomy, zero shared tokenizer ids, carrier-wrapped, DEC-011),
the standardized statistic, the family-wise max-statistic correction (no BH),
`N_PERM = 400`, model `unsloth/gemma-2-2b` at revision
`25319945f7fd83b8b903e12081777b7eef2ba993` in bf16. Keeping these fixed is what
makes a change in the result attributable to the varied axis.

### 2. Injection-rate axis (positive control only)

The injection grid `rate ∈ [0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20,
0.40]` (frozen, DEC-016/018) is exercised on the **positive-control arm at the
frozen config only** — it is not crossed with the 36-cell real-arm grid, because
the real arm injects nothing by construction.

**Order of reading is frozen.** Constructibility first (DEC-019): the plant must
raise the target feature's activation in *both* domains, and that feature must sit
inside `[lo, hi]`. Only then is the recovery curve read. A control that is not
shown constructible invalidates the measurement; it does not count as a negative.

**Recovery bar.** The frozen #145 criterion — recovery at an injected rate at or
below the grid's mid-range. The red team reports whether the #144 split's
documented bar-lowering (dropping "at/below mid-range") changes the recovery
verdict, and states that finding explicitly.

### 3. Conditional hook cell (axis E)

Axis E is pre-registered **conditionally**, because the canonical release may not
expose a layer-13 residual SAE and this document does not assume it does:

- **Mandatory cell:** `layer_12/width_16k/canonical` (`blocks.12.hook_resid_post`).
  This is the frozen hook and always runs.
- **Conditional cell:** `layer_13` residual at the same width/kind, run **only if**
  the `gemma-scope-2b-pt-res-canonical` release exposes it. If it does not, the
  cell is reported as `not_runnable: release exposes no layer_13 residual` — a
  reported outcome, not a silent omission.

This keeps the grid honest: the exact depth-fraction analogue is *attempted*, and
its absence is *recorded*, rather than the axis being quietly dropped.

### 4. Independence constraint (the point of the exercise)

The executor of steps 2-3 (#152, #153) **reimplements from
`RUNG3_PREREGISTRATION.md` alone.** It must not read or adapt the #143-#145 run
artifacts — including `experiments/2026-10-19-rung3-real-arm.py`, the probe, and
the results JSONs. The protocol is the pre-registration's, not a fresh choice
(DEC-005). Reading the original implementation would re-introduce the common-mode
failure #150 was filed to remove.

### 5. Decision rule (frozen)

The rung-3 null **survives** the red team only if **every** pre-registered cell
reports `n_survivors = 0` under its own family-wise cutoff.

**Any survivor in any cell re-opens the question** rather than closing it: it is
reported as a divergence, and the null is not upgraded. This is the #150
acceptance criterion 5, frozen before the run so it cannot be relaxed after.

### 6. Outcome table format (frozen)

One row per cell, written to a results JSON and pasted in full in the #153 done
comment:

| cell_id | seed | MIN_SUPPORT | CO_CHANCE_CAP | firing_rule | hook | n_family | best_z | cutoff | n_survivors | survivor_ids |
|---|---|---|---|---|---|---|---|---|---|---|

`cell_id` is a stable `g-<seed>-<support>-<cap>-<rule>-<hook>` string. Cells are
reported in `cell_id` order. The frozen reference cell is included in the table.

### 7. Bias audit — what the red team changes vs keeps

Feeds #154's required bias-audit section. Pre-registered here so the red team
declares it *before* running:

| #145 choice | Red-team action | Reason |
|---|---|---|
| Band support floor `5` | **Changed** (axis A) | The one free constant in the `lo` rule. |
| Band cap `0.5` | **Changed** (axis B) | The one free constant in the `hi` rule. |
| Firing rule `gt0` only | **Changed** (axis C) | #145 read `pct95` but the null must hold under both. |
| Seed `11` | **Changed** (axis D) | Single-seed evidence is the common-mode weakness. |
| Hook `blocks.12` | **Kept primary, layer-13 attempted** (axis E) | Layer 12 is the closest keyed hook; layer 13 is the exact analogue. |
| Corpus construction (DEC-011) | **Kept** | The input gate is a protocol invariant, not a variation. |
| Standardized statistic + family-wise max correction | **Kept** | This is the DEC-027 fix, not a knob. |
| `N_PERM = 400` | **Kept** | Keeps the cutoff construction byte-for-byte rung-2. |
| Positive-control order (constructibility first) | **Kept** | DEC-019; re-reading order is not a legitimate variation. |

Where a result diverges from #145, #154 states which of these actions it is
attributable to.

### 8. Cost bound

Grid cells at the frozen hook reuse activations encoded **once** (the encode is
the expensive step: #39 measured load 114.5 s, SAE load 17.9 s, 163 ms/prompt at
batch 64). Band derivation and `evaluate()` (400 permutations over the family) are
cheap and run per cell from the cached activations. Axis E requires a second
encode only if the layer-13 cell runs. The grid is sized so the model is loaded
**once**.

### 9. Falsifier of this document

This pre-registration is falsified by any of:

1. A cell run whose parameters are not in §1's frozen set → the cell is a
   deviation, reported as such, and does not count toward the decision rule.
2. A cell omitted from the report → file-drawer; the replication is void.
3. The independence constraint (§4) violated → the exercise is not adversarial
   and its verdict is not an upgrade.

### 10. References

- `docs/reference/RUNG3_PREREGISTRATION.md` — the frozen measurement protocol.
- `docs/decisions/LOG.md` — DEC-005 (freeze before the run) · DEC-011 (input gate)
  · DEC-016/018 (injection grid, p-value floor) · DEC-019 (constructibility first)
  · DEC-024 (bounded family) · DEC-027 (standardized statistic) · DEC-033 (rung
  ladder).
- #150 (the commission, split) · #151 (this step) · #152/#153/#154 (execution).
- #145 (the null under replication) · #144 (the positive control) · #143 (the
  probe) · #39 (feasibility and cost).
