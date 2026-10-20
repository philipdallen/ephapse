# Composition pre-registration §11 — precondition verification record

**Issue:** #165 (kind:gap) · **Directive:** DEC-043
**Run:** `20261020-0340-wmkm` · **Compiled:** 2026-10-20
**Verifies:** `docs/reference/COMPOSITION_PREREGISTRATION.md` §11 (on `main` via PR #157, unmerged)

§11 names five preconditions on the Phase 1 probe. This record ties each to a
repo path so a reader can confirm from `main` alone whether the run met it. Two
are met, one is partial, one is not on `main`, one is not yet applicable.

| §11 | Precondition | State | Repo path / evidence |
|---|---|---|---|
| 1 | Ratification (DEC-043) | **NOT ON `main`** | `docs/decisions/LOG.md` DEC-043 and `docs/reference/COMPOSITION_PREREGISTRATION.md` exist only on PR #157 (unmerged). `grep -c DEC-043 docs/decisions/LOG.md` = 0 on `main`. |
| 2 | Tokenization check (§3) | **MET** | `experiments/composition_phase1_tokenization_check.py` + `experiments/composition_phase1_word_lists.json` (commit `3c1e80b`). Result in that commit's message: checked=82 pass=82 fail=0 over 246 carrier-instances. |
| 3 | Carriers + word lists frozen; mismatch seed committed | **PARTIAL** | Lists frozen in `experiments/composition_phase1_word_lists.json` (commit `3c1e80b`). Seed **not committed and not recoverable** (see below). |
| 4 | Prior-art verification (§12) | **MET** | `docs/reference/COMPOSITION_PRIOR_ART.md` (commit `92a5813`). Verdict PROCEED. |
| 5 | Phase 2 frequency source named | **N/A to Phase 1** | §11.5 is "before Phase 2 runs"; Phase 2 is not authorized until G1–G4 pass (#158 scope note). |

## Recovery pin — target checkpoint revision

The composition probe inherits the rung-2 configuration, which named the model
only as `pythia-70m-deduped` with no revision pin. Pinned here the way rung 3
pinned its mirror (`experiments/2026-10-19-rung3-probe.py`, `MIRROR_REVISION`):

- `EleutherAI/pythia-70m-deduped` @ `e93a9faa9c77e5d09219f6c868bfc7a1bd65593c`
  (HF repo sha, last modified 2023-07-09).

Recorded in `experiments/2026-09-19-cross-domain-probe.py` as `MODEL_REVISION`
and passed to `HookedTransformer.from_pretrained`.

## Mismatch-generation seed — measured unrecoverable

§11.3 requires "the mismatch-generation seed committed in the same change". It
is committed nowhere. Measured 2026-10-20:

- No seed literal appears in any repo path, the PR #157 diff, or any issue
  comment (`grep -rn seed` over `docs/ experiments/`; PR #157 diff).
- The 18 mismatched pairs (`experiments/composition_phase1_word_lists.json`) are
  **not reproducible** from the published pools: the adjective `loud` (pair 18,
  "loud democracy") appears in **no** Appendix A pool — not the idiom, common,
  or novel adjective sets. The generation pool is therefore larger than anything
  recorded in the repo.
- A bounded brute-force over the plausible pools (Appendix A adjective/noun
  sets, their union, and the union plus `loud`; `random.Random(seed).choice`
  and `shuffle`, seeds 0–200k) produced **no** match.

Consequence: §11.3 cannot be satisfied from `main`, and the frozen list is the
only authoritative artifact. Resolving it needs either the seed value from the
author, or a decision to treat the frozen list as provenance and record the seed
as unrecoverable.
