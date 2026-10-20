# Composition emergence pre-registration: a new Ephapse probe line

**Directive:** DEC-043 (`docs/decisions/LOG.md`). **Ratified by Phil in chat,
2026-10-19** (out-of-band ratification per the DEC-041/DEC-042 precedent).
Phase 1 probe issue: ephapse #NNN. The Phase 1 probe traces to DEC-043, per the
directive-first protocol; Phase 2 is authorized only if Phase 1's gates G1-G4
pass (§8) and will be filed as a separate issue then.

**Date:** 2026-10-19 · **Status:** RATIFIED under DEC-043 (parameters frozen).
Changes after this point are amendments requiring a new directive, not silent
edits. (§11 preconditions 2-5 remain preconditions on the probe.)

**Scope:** this document specifies what the composition-emergence probe computes
and with what thresholds. It does **not** run the probe, and it contains no
measurement of the model. It covers two phases: Phase 1 (small constructed set,
gated) and Phase 2 (large corpus sweep, gated on Phase 1).

**The rule this document exists to honor.** The main detector line learned, at
cost, that a measurement must be specified before it is run: DEC-005 (freeze
method before the run), DEC-016 (the correction that could not fire), DEC-027
(standardize before cutting). This probe is a new claim in a new neighborhood,
so it gets the same discipline from the start: definitions before measurement,
controls before reading, falsifiers written down before data exists.

---

## 1. The question, and what it is not

**The question.** When two words compose ("blue" + "car" into "blue car"), do SAE
feature co-activations appear that were present in **neither** constituent alone?
That is composition emergence: the composite represented as something over and
above its parts.

**What it is not.** This is not the cross-domain bridging claim of spec section
1. The bridging detector asks whether one feature fires in two unrelated
domains. This probe asks whether one composite fires features that its two
constituents do not. Different unit (word and word-pair, not passage and
domain), different statistic (emergence, not bridging), different null. A result
here neither confirms nor threatens the bridging line.

**What a positive result would not claim.** An emergent feature is a statistical
observation, not a finding (the same discipline as the main detector). It would
not identify what the feature means (no autointerp claims are made here), and it
would not claim the model "understands" composition.

---

## 2. Definitions (before measurement)

- **Constituent.** A single word embedded in a carrier sentence, e.g. "blue" in
  "The report mentioned the blue here yesterday."
- **Composite.** Two words embedded in the *same* carrier sentence in the same
  slot, e.g. "blue car" in "The report mentioned the blue car here yesterday."
  Only the target changes; the carrier is byte-identical otherwise.
- **Target span.** The token positions covering the target word or word pair.
  Activations are read only over this span; the carrier is context, not signal.
- **Feature profile F(x).** The set of SAE features firing on input x, where a
  feature fires on x iff its maximum activation over the target span is > 0
  (the gt0 rule) in a majority (at least 2 of 3) of the fixed carrier sentences
  (Appendix B). Majority vote across carriers guards against carrier-specific
  artifacts.
- **Emergent feature (primary statistic).** For composite c with constituents a,
  b: a feature f with f in F(c), f not in F(a), f not in F(b). Count
  E(c) = |F(c) \ (F(a) union F(b))|; rate e(c) = E(c) / |F(c)|. Guard: if
  |F(c)| = 0 the pair is dropped and recorded; a dropped pair is a data-quality
  event, not a zero.
- **Emergent pair (secondary statistic).** Features f, g co-fire on input x iff
  both are in F(x). Let P(x) be the set of co-firing pairs within F(x). An
  emergent pair for c co-fires on c and on neither constituent. Count
  EP(c) = |P(c) \ (P(a) union P(b))|; rate ep(c) = |EP(c)| / |P(c)|, same guard.
  Pairs are restricted to features firing on the composite; the full feature
  cross product is not enumerated.
- **Class.** One of: idiom, common compositional, novel, verb+object
  (exploratory), synonym (calibration), mismatched (null). Word lists in
  Appendix A.
- **Class emergence.** The mean of e(c) (primary) or ep(c) (secondary) over the
  pairs in the class.

---

## 0. Transfer table: what carries from the 70M detector and what is new

| Parameter | 70M detector value | Composition probe value | Transfers? |
|---|---|---|---|
| Model | `pythia-70m-deduped` | same (Phase 1 default) | **Transfers** |
| SAE release | `pythia-70m-deduped-res-sm` | same | **Transfers** |
| Hook | `blocks.3.hook_resid_post` | same | **Transfers** (same measurement point as rung 2) |
| Firing rule (primary) | `gt0` | `gt0`, max over target span, majority of 3 carriers | **Transfers**, span rule newly specified (§2) |
| Correction construction | family-wise max-statistic, 400 permutations, no BH | same construction over class means (§4) | **Transfers** (the DEC-016/027 lesson is claim-independent) |
| N_PERM | 400 | 400 | **Transfers** |
| Selectivity band | `[0.05, 0.60]` per domain | **not applicable** (replaced by pair classes) | Does not transfer; family concept re-specified |
| Input corpus | 120 cooking / 120 astronomy passages | carrier-wrapped word lists (Appendix A) | **Newly specified** |
| Positive control | planted token "Zorblat" | idiom class (§6) | **Newly derived** (the analogue: a case where emergence is expected by construction of meaning) |
| Precision / harness | existing probe harness | same harness lineage | **Transfers** |

---

## 3. Inputs and carriers

**Carrier discipline (DEC-023 lineage).** The carrier-wrap exists so that only
the target differs between conditions. Three fixed carrier sentences for
adjective+noun targets (Appendix B); three for verb+object targets with the verb
in gerund form in all three conditions ("They discussed eating after lunch.",
"They discussed apples after lunch.", "They discussed eating apples after
lunch."). The gerund normalization keeps the verb-arm carrier grammatical and
identical across conditions.

**Phase 1 constructed set.** Tens of pairs per class, lists frozen in Appendix
A: 18 idioms, 18 common compositional, 18 novel, 18 mismatched, 10 synonym
pairs, 10 verb+object. The mismatch pairs were generated by seeded shuffle of
the adjective and noun pools; the seed is committed with the adopting change.

**Tokenization precondition.** Before any result is read: verify that each
composite's target span tokenizes as the concatenation of its constituents'
tokenizations in the carrier. A pair failing this check is excluded and
recorded, because "new" features could otherwise be tokenization artifacts
rather than composition effects. This is a precondition on reading, not a gate
on running.

**Cost estimate.** Phase 1 is roughly 170 unique words plus 46 composites, each
in 3 carriers: under 700 forward passes at 70M, minutes at batch 64. Phase 2 is
on the order of 12,000 passes, tens of minutes. Neither phase needs the 15 GiB
sandbox ceiling; both fit the standard probe budget.

---

## 4. Statistics

**Primary: feature-level emergence.** Per composite c, e(c) as defined in §2.
Per class, the mean of e(c).

**Secondary: pair-level emergence.** Per composite c, ep(c) as defined in §2.
Per class, the mean of ep(c). Reported alongside the primary for comparability;
a discovery claim may rest on either, but both are computed.

**Multiplicity (frozen construction, re-derived numbers).** The DEC-016/027
discipline transfers as a construction, not as numbers:

- *Discovery check* (common, novel, verb+object classes): pool the emergence
  values of the three discovery classes with the mismatched class. Under the
  null, class labels are exchangeable. Permute labels 400 times; per
  permutation compute class means and take the maximum over the three discovery
  classes; the cutoff is the 95th percentile of the 400 maxima. A class clears
  iff its observed mean exceeds that cutoff. BH-FDR is not used, for the
  DEC-016 reason.
- *Idiom positive-control bar* (separate, direct): the mean idiom emergence must
  exceed the 95th percentile of the 18 mismatched-pair emergence values. No
  permutation; a strict direct bar, pre-registered.
- *Synonym noise check* (conjunctive): for each synonym pair and carrier,
  d = Jaccard distance between the two single-word profiles (1 minus
  intersection over union). The noise floor is the 95th percentile of the 30
  values. A discovery claim for a class additionally requires that class's mean
  emergence exceed this floor. Note the asymmetry, recorded honestly: synonyms
  are single words while composites are two, so span effects make this floor
  easier to clear than the mismatched comparison. The mismatched comparison is
  the binding one (same two-word structure); the synonym floor is the sanity
  bound. Both must pass.

---

## 5. Controls

Three controls, three distinct jobs:

1. **Idiom class = positive control.** "Red herring" means something its
   constituents do not; if the instrument can detect composition at all, it
   should detect it here. Judged by the direct bar in §4.
2. **Synonym pairs = calibration.** "Car" vs "automobile" in identical carriers
   measures how much a profile jitters under semantic identity. This is the
   noise floor, not the null.
3. **Mismatched pairs = null base rate.** Adjective plus unrelated noun
   ("blue democracy") measures how much "emergence" appears under
   non-compositional pairing: tokenization noise, span effects, chance. This is
   the base rate every class is judged against.

---

## 6. Confounds

**Bigram frequency in training data.** "Blue car" and "red herring" are familiar
phrases; emergence there could be memorized-phrase recognition rather than
composition. The class contrast is the pre-registered control for this: the
novel class ("grateful toaster") is unfamiliar by construction. If idioms and
common pairs show emergence while novel pairs sit at the mismatched base rate,
emergence tracks familiarity, not composition (falsifier F3, §7). An explicit
frequency regression against a named public n-gram source is a Phase 2
optional; the class contrast is the primary control and needs no external data.

**Carrier and position effects.** The carrier is byte-identical across the three
conditions for each pair, and the majority-vote rule (§2) suppresses
carrier-specific features. Residual position effects (the composite occupies
more span) are absorbed by the mismatched base rate, which shares the two-word
structure.

**Feature absorption.** The prior-art record establishes that SAE features
co-occur above chance by construction. The emergence statistic is a difference
(composite minus constituent union), so construction-level co-occurrence
present in the constituents is subtracted out by design; what remains must be
attributable to the pairing.

---

## 7. Falsifiers

Written before data exists; a fired falsifier is a result, not a failure:

- **F1. Idiom bar fails.** Mean idiom emergence does not exceed the 95th
  percentile of mismatched emergence. Verdict: instrument failure. Word-level
  gt0 profiles at `blocks.3.hook_resid_post` cannot detect composition. The line
  closes at Phase 1. Composite-class results are not read as composition
  findings.
- **F2. Clean null with validated instrument.** The idiom bar passes but no
  discovery class clears both bars. Verdict: composition is additive at this
  layer and scale, a preservable negative. Decision hook: Phil decides whether
  a 2B repeat is pre-registered as a new document; it is not an extension of
  this one.
- **F3. Familiarity confound.** Idiom and common classes clear, novel class at
  mismatched base rate. Verdict: emergence tracks bigram familiarity, not
  composition. Close with the confound recorded; Phase 2 does not run on the
  composition claim.
- **F4. Noise dominance.** The synonym floor exceeds every class mean.
  Verdict: measurement noise dominates the signal at this configuration. Stop
  before Phase 2.

---

## 8. Phase 1 gates and decision hooks

Phase 1 runs iff this document is ratified. Phase 2 runs iff all four gates
pass:

- **G1. Instrument validated.** Idiom bar (§4) passes. If not, F1 fires.
- **G2. Phenomenon beyond idioms.** At least one of {common, novel} clears the
  discovery cutoff and the synonym floor. If not, F2 fires.
- **G3. Not familiarity alone.** If only the common class clears while the
  novel class sits at base rate, F3 fires instead of promotion.
- **G4. Tokenization precondition (§3) holds** for every pair read; failures
  excluded and recorded.

Decision hooks: all gates pass, file the Phase 2 issue with §9 parameters,
tracing to the ratified decision. Any falsifier fires, close the line with the
recorded verdict and file nothing further. F2 with a validated instrument
additionally offers Phil the 2B-repeat decision as a separate pre-registration.

---

## 9. Phase 2 specification (gated on §8)

- **Corpus.** Noun pool (400, committed list) by adjective pool (150, committed
  list); seeded random sample of 2,000 adjective+noun composites plus 2,000
  seeded mismatched pairs; synonym set carried from Phase 1. Verb+object arm:
  200 verbs by 400 nouns, seeded sample of 2,000 composites. All pools, lists,
  and seeds committed before the Phase 2 run.
- **Statistics.** Identical to §4 (primary, secondary, discovery permutation
  null, synonym floor). Cutoff *numbers* are re-derived from Phase 2's own
  permutation null; the *construction* is frozen here. This is the rung-3
  lesson: transfer the construction, re-derive the numbers.
- **Optional frequency regression.** Correlate per-pair emergence with bigram
  log-frequency from a named public n-gram source, as a direct test of the §6
  confound. Open precondition: the source must be named and committed in the
  Phase 2 issue before the run; the class contrast remains the primary control.

---

## 10. Environment

- **Model:** `pythia-70m-deduped` (DEC-014 target). **SAE:**
  `pythia-70m-deduped-res-sm`. **Hook:** `blocks.3.hook_resid_post`. Same
  measurement point as the rung-2 detector, so a composition result is
  comparable to the bridging results at this scale.
- **Harness:** the existing probe harness lineage
  (`experiments/2026-09-19-cross-domain-probe.py`), extended with the
  carrier/span/profile machinery of §2. Precision and batching follow the
  harness; record both in the probe header.
- **2B scale** (`gemma-2-2b`, Gemma Scope layer 12) is a later question. It
  requires its own pre-registration (band re-derivation does not apply here,
  but the class machinery would need re-validation); it is not an arm of this
  document.

---

## 11. Open preconditions the probe must resolve first

1. **Ratification.** This document is a draft until Phil ratifies it under
   DEC-041. Nothing runs before that.
2. **Tokenization check** (§3) implemented and passing before results are read.
3. **Carrier sentences** (Appendix B) and **word lists** (Appendix A) frozen by
   adoption; the mismatch-generation seed committed in the same change.
4. **Prior-art verification** (§12) completed against primary sources before
   the Phase 1 run.
5. **Phase 2 frequency source** named before Phase 2 runs (§9).

These are preconditions on the probe, not on this document. The draft is
complete without them; the probe is not.

---

## 12. Prior-art note

The relevant neighborhood is compositionality in neural language models and
nonlinear / non-atomic SAE features. This document asserts **no** specific
paper claims as verified. Before the Phase 1 run, the prior-art neighborhood
must be checked against primary sources (the standing lesson from the
AxBench/DEC-034 episode: prior-art latency is the expensive failure mode).
What the check must establish: whether emergent-feature-under-composition has
been measured before, with what instrument, and at what scale; and whether any
existing result already answers the Phase 1 question. If it does, this probe
does not run.

---

## 13. References

- `docs/reference/RUNG3_PREREGISTRATION.md`: the contract pattern this
  document instantiates (definitions, transfer table, frozen construction with
  re-derived numbers, falsifiers before data).
- DEC-005 (freeze method before the run) · DEC-011 (input-disjointness gate,
  here as carrier discipline) · DEC-014 (target model) · DEC-016 (the correction
  that could not fire) · DEC-023 (carrier wrap, context) · DEC-024 (bounded
  family, here as bounded classes) · DEC-027 (standardize; the recurring-bug
  rule) · DEC-041 (directive-first; this document's draft status).
- `experiments/2026-09-19-cross-domain-probe.py`: the harness lineage.

---

## Appendix A. Phase 1 word lists (frozen on adoption)

**Idioms** (adjective+noun, non-compositional meaning): red herring, white
elephant, black sheep, green room, blue moon, silver lining, cold shoulder, hot
potato, wet blanket, dead ringer, dark horse, red tape, white lie, cold turkey,
sour grapes, blue chip, green light, big fish.

**Common compositional** (adjective+noun, literal): blue car, red apple, wooden
table, glass window, hot coffee, cold water, big dog, small house, new book, old
tree, fast train, slow river, green field, black cat, white snow, warm bread,
fresh paint, dry sand.

**Novel** (adjective+noun, grammatical but bizarre): grateful toaster, sleepy
arithmetic, fragile thunder, polite avalanche, anxious trombone, bitter
telescope, curious pebble, purple democracy, wooden thunder, sleepy trombone,
grateful arithmetic, anxious pebble, fragile democracy, polite toaster, bitter
avalanche, curious thunder, purple arithmetic, silent telescope.

**Mismatched** (adjective + unrelated noun; seeded shuffle of the pools): blue
democracy, wooden thunder, grateful pebble, anxious toaster, sleepy trombone,
fragile arithmetic, polite avalanche, bitter telescope, curious thunder, silent
pebble, purple toaster, red democracy, hot arithmetic, green trombone, black
pebble, white arithmetic, dry telescope, loud democracy.

**Synonym pairs** (calibration): car/automobile, sofa/couch, happy/glad,
fast/quick, big/large, small/little, begin/commence, end/finish, buy/purchase,
street/road.

**Verb+object** (exploratory arm, gerund in carrier): eating apples, reading
books, driving cars, writing letters, building houses, drinking water, opening
doors, closing windows, planting trees, catching fish.

---

## Appendix B. Carrier sentences (frozen on adoption)

Adjective+noun targets:
1. "The report mentioned the TARGET here yesterday."
2. "She wrote down the TARGET on the form."
3. "They discussed the TARGET after lunch."

Verb+object targets (verb in gerund form in every condition):
1. "They discussed TARGET after lunch."
2. "She finished TARGET before noon."
3. "He described TARGET in detail."
