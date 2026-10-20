# Composition-emergence Phase 1: prior-art verification

**Issue:** #159 (step 1/3 of the #158 decomposition) · **Directive:** DEC-043
**Run:** `20261020-0200-2vrx` · **Compiled:** 2026-10-20
**Verifies:** `docs/reference/COMPOSITION_PREREGISTRATION.md` §12 (on `main` via PR #157)

This is the prior-art check §12 requires before the Phase 1 probe runs. It is
organized around the four questions §12 names, answered against **primary
sources** — arXiv abstracts and the sources already catalogued in
`docs/reference/PRIOR_ART.md`. The standing lesson it serves is DEC-034: the
AxBench episode, where prior-art latency was the expensive failure mode.

**Verdict: `PROCEED`** — no existing result answers the Phase 1 question. Three
closely related lines exist and must be cited by the pre-registration; one of
them predicts the *opposite* of the probe's alternative hypothesis and sharpens
what Phase 1 should claim. See "Consequence" below.

---

## Q1. Has emergent-feature-under-composition been measured before?

Not in the sense Phase 1 asks. Phase 1 asks whether a **feature** (an SAE
latent) appears for a composite that was present in **neither constituent
alone**. The nearest measured constructs are adjacent but distinct:

- **SAE Additivity Residuals (SAR)** — *Behavioral Compositionality of Sparse
  Autoencoder Representations*, arXiv:2610.21261 (2026-10-15). Measures the
  behavioral variation left unexplained above a chosen interaction order, and
  compares learned SAE coordinates against sum-preserving random rotations.
  Finds lower first-order residuals for learned coordinates across all 18 model
  and behavior settings, but that coordinates are **not fully additive**:
  pairwise terms improve held-out coalition ordering everywhere. This measures
  *interaction terms above linear superposition* — not the appearance of a new
  latent.

- **PolySAE** — *Modeling Feature Interactions in Sparse Autoencoders via
  Polynomial Decoding*, arXiv:2602.01322 (2026-02-01). Extends the SAE decoder
  with higher-order terms so interactions are representable at all; explicitly
  motivated by the observation that "linear models cannot distinguish whether
  'Starbucks' arises from the composition of 'star' and 'coffee' features or
  merely their co-occurrence." Reports learned interaction weights are
  negligibly correlated with co-occurrence frequency (r = 0.06 vs 0.82 for SAE
  feature covariance).

- **OrtSAE** — *Orthogonal Sparse Autoencoders Uncover Atomic Features*,
  arXiv:2509.22033 (2025-09-26). Treats **feature composition** as a defect to
  reduce: independent features merging into composite representations. Reports
  a 15% reduction in composition. This is the *opposite framing* to Phase 1:
  it treats composite latents as an artifact of an entangled dictionary rather
  than as an emergent phenomenon to detect.

**Nothing found** that measures emergence as a class-level rate on a
constructed word set with a permutation null, an idiom positive control, and a
synonym noise floor. The three above measure interaction structure or
dictionary entanglement, not per-composite latent emergence against a
frequency-matched control.

## Q2. With what instrument?

All use **SAE feature sets on transformer activations**, with one important
split in instrument:

| Work | Instrument | Nonlinear? |
|---|---|---|
| SAR (2610.21261) | SAE coordinates + higher-order interaction terms | yes |
| PolySAE (2602.01322) | polynomial (low-rank tensor) decoder over SAE features | yes |
| OrtSAE (2509.22033) | SAE training objective (orthogonality penalty) | SAE-level |
| Phase 1 (#161) | vanilla SAE latents, carrier-wrapped inputs, permutation discovery check | no |

Phase 1's instrument is the **vanilla** SAE — it reads existing latents and asks
which are newly present. That is the instrument the probe intends, and no prior
work runs it for this question.

## Q3. At what scale?

- SAR: 18 model/behavior settings (scale not specified in abstract; behavior-level).
- PolySAE: four language models and three SAE variants (GPT-2 among them).
- OrtSAE: multiple models and layers.
- Phase 1: `pythia-70m-deduped`, one SAE (`pythia-70m-deduped-res-sm`), hook
  `blocks.3.hook_resid_post`.

Phase 1 is at a **smaller scale than any of the three**, which is a known and
accepted limit of the line (the same 70M limit the rung-3 chain addresses by
moving to `gemma-2-2b`). A Phase 1 null would be a null at 70M and would need
saying so.

## Q4. Does any existing result already answer the Phase 1 question?

**No.** None of the three measures emergent latents under composition on a
constructed set, so none answers it. But SAR (2610.21261) is close enough that
it constrains the interpretation, and that is the finding that matters:

- SAR shows SAE coordinates are **not fully additive** and that pairwise
  interaction terms are real and improve held-out ordering in **every** setting
  tested. The Phase 1 alternative hypothesis is therefore already partly
  established *in principle*: composition is not purely additive at the SAE
  layer.
- What SAR does **not** do is attribute that non-additivity to **new latents**
  rather than to **interaction between existing latents**. That is exactly the
  gap Phase 1's e(c) / ep(c) pair (primary emergent-feature rate, secondary
  emergent-pair rate) is designed to probe.

So the Phase 1 question is not answered, but it is now sharper: it is not "is
composition non-additive?" (SAR says yes, generally) but "does non-additivity
show up as **emergent single latents** — and do those track composition or
bigram familiarity?" (G3's confound). Phase 1's idiom positive control and
synonym noise floor are what make it a distinguishable question from SAR.

## Consequence — required amendment before Phase 1 runs

`PROCEED`, with one amendment the pre-registration must absorb (a deviation to
be recorded, not a silent update):

1. **Cite the three sources in §12** — SAR (arXiv:2610.21261), PolySAE
   (arXiv:2602.01322), OrtSAE (arXiv:2509.22033) — replacing §12's current
   "asserts no specific paper claims as verified" with the four-question answer
   above.
2. **Record SAR as the closest prior result and the reason Phase 1 is still
   worth running**: SAR measures interaction terms, not emergent latents, and
   at behavior level rather than on a constructed, frequency-controlled set.
3. **Framing constraint on the writeup:** a Phase 1 positive must be stated as
   *emergent latents beyond the interaction structure SAR already reports*, not
   as the discovery that composition is non-additive. A writeup claiming the
   latter would overclaim against SAR.

None of this blocks the probe. It changes what a positive result is allowed to
claim, which is the point of a prior-art check.

## Sources

| Topic | Reference |
|---|---|
| SAE additivity residuals; non-additivity of SAE coordinates | arXiv:2610.21261, *Behavioral Compositionality of Sparse Autoencoder Representations* (2026-10-15) |
| Polynomial decoder for feature interactions; co-occurrence independence | arXiv:2602.01322, *PolySAE* (2026-02-01) |
| Feature composition as a dictionary defect; 15% reduction | arXiv:2509.22033, *OrtSAE: Orthogonal Sparse Autoencoders Uncover Atomic Features* (2025-09-26) |
| Method for co-occurrence beyond chance (NPMI + injected ground truth) | LessWrong, *Towards data-centric interpretability with sparse autoencoders* — catalogued in `docs/reference/PRIOR_ART.md` §2 |
| Feature absorption / splitting | arXiv:2409.14507 (Chanin et al.) — `docs/reference/PRIOR_ART.md` §4 |
| SAE vs simple baselines on detection (DEC-034) | AxBench, arXiv:2501.17148 (Wu et al., ICML 2025) — `docs/reference/PRIOR_ART.md` Sources |

Search method: arXiv API (`export.arxiv.org/api/query`), queries over
`"sparse autoencoder"` crossed with `compositionality`, `composition`,
`constituent`, `idiom`, `phrase`, and `emergent`; abstracts read for the four
candidates returned. No secondary sources were used for the verdict.
