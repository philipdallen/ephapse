# DEC-043 shareable data bundle — manifest and dataset card

**Issue:** #176 (agent-side work of #175, critique outreach) · **Directive:** DEC-043
**Run:** `20261022-0102-gehl` · **Compiled:** 2026-10-22

This document is the bundle's manifest and its dataset card. It inventories the
files the DEC-043 critique ships, states what each one is and which decision or
experiment it traces to, and gives the card a critic can read on its own.

**Nothing here is uploaded.** The Hugging Face dataset upload and the LessWrong /
Alignment Forum post are owner steps under #175; this document only prepares the
material and traces every figure to a record.

## Scope caveat — DEC-043 is not on `main`

`docs/decisions/LOG.md` on `main` ends at DEC-042; `grep -c DEC-043
docs/decisions/LOG.md` = 0. The DEC-043 text and its frozen pre-registration
(`docs/reference/COMPOSITION_PREREGISTRATION.md`) exist only on the unmerged PR
#157. This is **already recorded** — `docs/reference/COMPOSITION_PREREGISTRATION_VERIFICATION.md`
§11.1 marks ratification `NOT ON main`, and #102/#165 carry it — so it is not a
new drift and is not filed again here. It is restated because a reader of this
bundle must know that the directive cited throughout is not yet on the default
branch.

---

## 1. Bundle manifest

Hashes are `sha256`, first 16 hex characters, of the `main` revision at the
commit named in the done comment. A `Traces to` column names the decision,
experiment, or issue that owns the file.

### 1a. The findings ledger and its gate

| File | sha256 (16) | What it is | Traces to |
|---|---|---|---|
| `findings.jsonl` | `e48be8e02f1db353` | The flagged-event log; every experiment record, positive or null | Workflow §6; gate G-E1–G-E8 |
| `findings.highwater` | `2e6d31a5983a9125` | Monotonic high-water mark for the ledger | tooling |

The ledger holds **9 data lines** at this revision:

| ts | issue | run_id | kind | verdict |
|---|---|---|---|---|
| 2026-09-18T23:29:47Z | #5 | 20260918-2329-zbmn | positive_control | flagged |
| 2026-09-19T02:13:28Z | #6 | 20260919-0213-tsm5 | paraphrase_robustness | flagged |
| 2026-09-19T02:13:28Z | #5 | 20260919-0213-tsm5 | positive_control_rerun | null |
| 2026-09-19T04:25:33Z | #7 | 20260919-0229-to3m | causal_positive_control | flagged |
| 2026-09-19T05:24:57Z | #3 | 20260919-0229-to3m | cross_domain_probe | null |
| 2026-10-19T05:14:00Z | #145 | 20261019-0501-ccdw | cross_domain_probe | null |
| 2026-10-19T16:20:00Z | #154 | 20261019-1602-3upj | redteam_replication | null |
| 2026-10-20T04:22:00Z | #161 | 20261020-0401-hq7k | composition_emergence_phase1 | flagged |
| 2026-10-20T05:45:00Z | #168 | 20261020-0541-0lli | gate_shape_sample | null |

`#168` is a **synthetic** record committed to exercise the gate-verdict shape
(its own note says "SYNTHETIC made-up class-mean emergence — not a
measurement"). It is listed for completeness and is **not** evidence for any
claim below.

### 1b. Rung 0–3 outputs (the detector line)

| File | sha256 (16) | What it is | Traces to |
|---|---|---|---|
| `experiments/2026-09-18-injected-positive-control-detector-validation.py` | `58ccf0236160e126` | Detector positive control: recovery vs injected-correlation rate | #5, DEC-019 |
| `experiments/2026-09-18-injected-positive-control-results-v4.json` | `fc2219ccf074e95f` | Its result (run 20260918-2332-e7c4): recovery 0.87 at rate 0.20 | #5, DEC-019 |
| `experiments/2026-09-19-cross-domain-probe.py` | `7783f45e7977f635` | Rung-2 cross-domain probe at pythia-70m | #3, DEC-027 |
| `experiments/2026-09-19-cross-domain-probe-results.json` | `26807491a04f54c8` | Its result: 0 survivors, best z 3.10 vs cutoff 4.41 | #3, DEC-027 |
| `experiments/2026-09-19-paraphrase-robustness.py` | `2a2bb10d6e81f1ef` | Surface-controlled paraphrase arm | #6 |
| `experiments/2026-10-19-rung3-probe.py` | `49388e05fe2c819c` | Rung-3 step 1: load model+SAE, derive selectivity band | #143 |
| `experiments/2026-10-19-rung3-probe-results.json` | `cc7e3530a1207a67` | Band `[0.0417, 0.7071]`, family 1109/16384 | #143 |
| `experiments/2026-10-19-rung3-positive-control.py` | `917d070669d690d5` | Rung-3 step 2: frozen `Zorblat` positive control | #144 |
| `experiments/2026-10-19-rung3-positive-control-results.json` | `8561400812f465df` | Its result: control **recovered** (run 20261019-0101-05fv) | #144 |
| `experiments/2026-10-19-rung3-real-arm.py` | `525cbe427f9e8774` | Rung-3 step 3: real cross-domain arm at gemma-2-2b | #145 |
| `experiments/2026-10-19-rung3-real-arm-results.json` | `fb48949a794096e1` | Its result: 0 survivors (run 20261019-0501-ccdw) | #145 |
| `experiments/2026-10-19-rung3-redteam-step2-results.json` | `f9406936f91dd6a8` | Red-team replication, cell `g-11-5-0.5-gt0-12` | #152 |
| `experiments/2026-10-19-rung3-redteam-step3-results.json` | `834145d3829bd3da` | Red-team grid: 73 cells, 0 with survivors | #153 |

### 1c. DEC-034 comparators

| File | sha256 (16) | What it is | Traces to |
|---|---|---|---|
| `experiments/2026-09-22-comparator-baselines.py` | `801f03539e7a9bd5` | SAE bridge beside difference-in-means and linear probe | #37, DEC-034 |
| `experiments/2026-09-22-comparator-baselines.json` | `dc2f7c7eebc40bac` | Its result: neither substrate detects a paraphrase-invariant bridge | #37, DEC-034 |

### 1d. Composition-emergence Phase 1 (DEC-043's own probe)

| File | sha256 (16) | What it is | Traces to |
|---|---|---|---|
| `experiments/2026-10-20-composition-phase1-probe.py` | `8306ba382a88c9ac` | Phase 1 probe, 82 conditions, pythia-70m-deduped @ `e93a9fa` | #161, DEC-043 |
| `experiments/2026-10-20-composition-phase1-probe-results.json` | `9244d68d79f3048c` | Its result: G1 FAIL, G2 FAIL, G3 PASS, G4 PASS | #161, DEC-043 |
| `experiments/composition_phase1_tokenization_check.py` | `df482bcec542be23` | §3 tokenization precondition check (G4) | #160, DEC-043 |
| `experiments/composition_phase1_word_lists.json` | `0d821fa4b984e647` | The frozen word lists the probe reads (a frozen **input**, not a result) | #160, DEC-043 |

### 1e. Governing records (the decisions the bundle cites)

| File | sha256 (16) | What it is | Traces to |
|---|---|---|---|
| `docs/decisions/LOG.md` | `3cf1422f54d5bf61` | Decision log (ends at DEC-042 on `main`) | all DECs |
| `docs/reference/RUNG3_PREREGISTRATION.md` | `fab4a572fd0b84ef` | What the rung-3 probe computes, frozen before the run | #40 |
| `docs/reference/REDTEAM_PREREGISTRATION.md` | `5c1855df8c85eaf6` | What the red team may vary, frozen before it ran | #150 |
| `docs/reference/REDTEAM_VERDICT_2026-10-19.md` | `04155ab5c5abd3c6` | The rung-3 null survives the red team | #150 |
| `docs/reference/COMPOSITION_PRIOR_ART.md` | `6e71ccd01b1c45da` | §12 prior-art verification, verdict PROCEED | #159, DEC-043 |
| `docs/reference/COMPOSITION_PREREGISTRATION_VERIFICATION.md` | `8acf355747a6733a` | §11 precondition record (ratification NOT ON main) | #165, DEC-043 |
| `docs/reference/GATE_VERDICT_RECORD_SHAPE.md` | `991a916c44dbef26` | The gate-verdict record shape | #167, DEC-043 |

### 1f. Not in this bundle

- **The DEC-043 pre-registration text** (`docs/reference/COMPOSITION_PREREGISTRATION.md`)
  — it exists only on unmerged PR #157, so it cannot be hashed from `main`. A
  critic needing it must read PR #157. Recorded, not fixed (see Scope caveat).
- **Model weights and SAEs.** The bundle ships records and scripts, not tensors.
  Models are named by id and revision in each result JSON.
- **`experiments/2026-10-19-rung3-probe-results-firing.npz`** — a binary firing
  matrix. Excluded from the manifest because it is large and machine-only; its
  provenance is the result JSON beside it.

---

## 2. Dataset card (draft)

### 2.1 The claim

Cross-domain co-activation in open-weight models is a useful **candidate
generator** for mathematical hypotheses. The second product is a **validation
layer** that separates *instrument failure* from *phenomenon absence* — a null
result is only informative once the instrument that produced it is shown to
recover a known-positive signal.

This bundle supports the *record so far*, not a positive claim. The record is:
the detector recovers an injected positive control; one weak bridging signal
survives surface control (6 survivors vs 0 under a shuffled null); then a clean
null at 70M (DEC-027), confirmed not to be an SAE artifact by supervised
comparators (DEC-034); the null reproduces at 2B (gemma-2-2b) with the positive
control recovering first (DEC-043 line, #144/#145); and the successor
composition-emergence line closed at Phase 1 on an **instrument failure**, not on
a null about composition.

### 2.2 The method

A probe measures **per-feature cross-domain co-activation**: for each SAE feature,
the rate at which it fires on passages from domain A paired with passages from
domain B, standardized against a **pairing-permutation null** (`N_PERM=400`). The
decision rule is a **family-wise max-statistic** on the standardized statistic —
the 95th percentile of the permutation distribution of the maximum per-feature z.
A feature is a *survivor* when its z exceeds that cutoff. BH-FDR is deliberately
**not** used (DEC-016).

The unit is the SAE feature read at one hook (residual stream, one layer). The
feature family is restricted to a **selectivity band** `[MIN_SUPPORT/n,
sqrt(CO_CHANCE_CAP)]` = `[0.0417, 0.7071]`, so that neither near-dead nor
near-always-on features can enter.

### 2.3 Controls

| Control | What it establishes | Record |
|---|---|---|
| Injected positive control | The detector recovers a signal that is known to be present | #5: recovery **0.87** at injection rate 0.20 vs 0.00 for a naive co-occurrence baseline (`...-results-v4.json`, run `20260918-2332-e7c4`) |
| Rung-3 frozen positive control | The 2B detector is not asleep before the real arm is read | #144: `Zorblat` planted at rate 0.10, **recovered** (run `20261019-0101-05fv`) |
| Shuffled null | The bridging signal is not an artifact of pairing | #6: matched 6 survivors vs **0** under the shuffled null |
| Supervised comparators (DEC-034) | The paraphrase null is not an SAE artifact | #37: linear probe at chance on the paraphrase arm (AUROC 0.448, bridge 0.23 below its own 0.33 cutoff) |
| Red-team grid | The 2B null is not an artifact of one parameter choice | #153: **73 cells, 0 with survivors**; #152 replicates the reference cell |

### 2.4 Falsifiers

The composition line (DEC-043) carries F1–F4 as its acceptance. Phase 1 fired
**F1 and F4**, and the line closes at Phase 1 by design:

- **F1 (idiom bar fails)** — instrument failure. The probe must recover the
  frozen idiom positive-control class. It did not: idiom mean `e` = **0.2562**,
  far below the bar **0.6231**. An instrument failure means the probe could not
  test the hypothesis at this layer/SAE — **not** that composition is absent.
- **F2 (clean null with validated instrument)** — would have been a preservable
  negative. Did not fire; F1 fired first.
- **F3 (familiarity confound)** — Phase 2 does not run on the composition claim.
  Not fired (Phase 2 was never authorized).
- **F4 (noise dominance)** — stop before Phase 2. **Fired**: no discovery class
  cleared the synonym noise floor 0.7428.

A falsifier firing with the recorded verdict means the decision was
well-specified, not that it was wrong.

### 2.5 Headline results

| Result | Figure | Record |
|---|---|---|
| Detector positive control | recovery **0.87** at rate 0.20 | #5, `...-results-v4.json` |
| Rung-2 bridging (weak, surface-controlled) | **6** survivors matched vs **0** shuffled | #6 |
| Rung-2 cross-domain null (70M) | **0** survivors, best z **3.10** vs cutoff **4.41** | #3, DEC-027 |
| DEC-034 comparator cross-cut | probe AUROC **0.448** on paraphrase arm (chance) | #37, DEC-034 |
| Rung-3 null (2B, gemma-2-2b) | **0** survivors, best z **3.695** vs cutoff **4.664**; family 1109/16384 | #145 |
| Rung-3 red-team | **73** cells, **0** with survivors | #153 |
| Composition Phase 1 | idiom `e` **0.2562** (bar 0.6231); G1 FAIL, G2 FAIL, G3 PASS, G4 PASS | #161, DEC-043 |

**Scale caveat (verbatim from the #145 record).** The rung-3 result's own
`verdict_caveat` reads: *"a null here is a null of the SAE instrument at 2B; the
comparator cross-cut (DEC-034) is untested at rung-3 scale, so the scale
explanation is not retired."* The null is an observation about an instrument, not
a mathematical result.

### 2.6 Provenance and licensing

Every result JSON is self-describing: it carries `run_id`, `issue`, the model id
**and revision**, the SAE release/id, the hook, dtype, device, the statistic, the
null model, and the correction. The models are public (`pythia-70m-deduped`;
`unsloth/gemma-2-2b` mirror of `google/gemma-2-2b`). License terms for the
bundle itself are the owner's call and are left to the upload step under #175.

---

## 3. Claim check (required before drafting)

Every figure above was checked against its source record on `main` at the
revision named in the done comment. The check is reproducible:

```bash
python3 - <<'PY'
import json
d = json.load(open('experiments/2026-10-19-rung3-real-arm-results.json'))
g = d['rules']['gt0']
print('rung3 best_z', round(g['best_z'],3), 'cutoff', round(g['cutoff_z'],3),
      'survivors', g['n_survivors'], 'family', g['n_family'])
p = json.load(open('experiments/2026-10-20-composition-phase1-probe-results.json'))
print('idiom mean_e', round(p['results']['idiom']['mean_e'],4))
PY
```

Observed: `rung3 best_z 3.695 cutoff 4.664 survivors 0 family 1109` and
`idiom mean_e 0.2562` — both match the card.

**Drift found: none.** Every figure in §2.5 traced to its record. The only
discrepancy surfaced is the already-recorded one — DEC-043 is not on `main`
(#102/#165) — which is restated in the Scope caveat and **not** re-filed, per the
issue's instruction not to carry an unverified figure: no unverified figure is
carried, and the missing directive is a recorded, known state rather than a
figure mismatch.
