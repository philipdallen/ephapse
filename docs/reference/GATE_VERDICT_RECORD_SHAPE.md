# Gate-verdict record shape — decision

**Issue:** #167 (step 1 of 3, split from #162) · **Directive:** DEC-043
**Run:** `20261020-0501-q7z3` · **Decided:** 2026-10-20
**Status:** decided — binds step 2 (#168) and every probe line whose
pre-registration defines gates and falsifiers.
**Changes no existing record.** This document records a shape; it does not
migrate one.

---

## 1. The question

`findings.jsonl` is single-event: one `verdict` (`flagged|null`) per probe run.
The composition pre-registration
(`docs/reference/COMPOSITION_PREREGISTRATION.md` §7–§8, on `main` via PR #157)
defines **four gates G1–G4** with independent acceptance conditions and **four
falsifiers F1–F4** whose firing is itself a pre-registered result. That is a
*vector* of verdicts, and the single-event schema cannot hold it.

The mismatch is not hypothetical. The Phase 1 run (#161, run
`20261020-0401-hq7k`) recorded its gate outcomes as

```json
"result": {..., "gates": {"G1": false, "G2": false, "G3": true, "G4": true},
                 "clears": {"common": false, "novel": false, "verb_object": false}},
"confounds_fired": ["instrument_failed_idiom_bar_not_cleared",
                    "no_discovery_class_above_synonym_floor"]
```

— the gate booleans nested inside `result`, documented nowhere, and the falsifier
firing written as a prose string into `confounds_fired`, a key whose meaning is
"which *confounds* fired". F1 firing is not a confound. That improvisation is
what this decision replaces, so the next run does not improvise a different one.

## 2. Decision

**Chosen: (a) — two new findings extension keys.**

A gate-style run records its verdicts on the findings line, in two keys declared
in `KNOWN_EXTENSIONS` (`tooling/gates/validate_findings.py`) and documented in the
`findings.jsonl` header:

| Key | Type | Meaning |
|---|---|---|
| `gate_verdicts` | object, `string → bool` | gate id → whether its pre-registered acceptance condition held |
| `falsifiers_fired` | list of `string` | ids of the pre-registered falsifiers that fired |

```json
"gate_verdicts": {"G1": false, "G2": false, "G3": true, "G4": true},
"falsifiers_fired": ["F1", "F4"]
```

**Exact semantics.**

1. **The key set is per pre-registration, not schema-fixed.** The ids are the
   ones the record's own pre-registration defines. `G1`–`G4` / `F1`–`F4` are the
   composition probe's; another line's may differ in count or naming. The schema
   fixes the *shape*, never the ids.
2. **Absent ≠ pass.** A gate id absent from `gate_verdicts` means **not
   evaluated**, and must never be read as a pass. `true` is the only value that
   means "held". A gate that cannot be interpreted in a run (the #161 record's
   `G3`, which is vacuously true once G1 fails) is omitted under this rule rather
   than marked `true`.
3. **Absent ≠ none fired.** `falsifiers_fired: []` means the pre-registration
   defines a falsifier set and none fired. The key absent means the
   pre-registration defines no falsifier set. The two are different facts and are
   not collapsed into one.
4. **Verdicts only; the numbers stay in `result`.** Class means, the discovery
   cutoff, the idiom bar, the synonym floor, the mismatched base rate, per-class
   `clears`, and the tokenization counts are the *inputs* a verdict is computed
   from, and they live in `result` (already a declared extension key).
   `gate_verdicts` never carries a statistic, so no number has two homes
   (PROGRAM_MANAGEMENT_SPEC §2, "derive, never duplicate").
5. **Prose stays in `note`** (already declared). The one-line justification for a
   failed gate or a fired falsifier goes there, not into `gate_verdicts`.

## 3. Why (a), not (b)

(b) — a separate verdict artifact linked from the findings entry — was rejected on
four grounds:

1. **Unit of record.** A gate verdict is a property of one probe run, which is
   exactly the unit of a findings line. (b) splits one run across two files and
   adds a link that can dangle.
2. **No second source of truth.** PROGRAM_MANAGEMENT_SPEC §2 forbids one. (b)
   creates a second artifact whose schema, append-only rule, and gate would each
   have to be built and kept in step with `findings.jsonl`.
3. **The mechanism already exists and is already gated.** The extension-key path
   costs one line in `KNOWN_EXTENSIONS` plus one header line, and
   `test_findings_header_declares_every_extension_key` already holds the two in
   step (the gate is strict about a key being *declared*, which is the property
   wanted here).
4. **The program-level axis already has a home.** The instrument-vs-phenomenon
   distinction is §3.2's `outcome` vocabulary, recorded in `program/ledger.jsonl`
   as program state. A separate verdict artifact would duplicate the ledger — and
   the ledger is deliberately not evidence (PROGRAM_MANAGEMENT_SPEC §4).

## 4. Orthogonality — how the new keys relate to `verdict` and `outcome`

Three axes, deliberately not collapsed:

| Axis | Field | File | Answers |
|---|---|---|---|
| observation | `verdict` (`flagged` \| `null`) | `findings.jsonl` | did the probe's statistic exceed its null |
| apparatus | `gate_verdicts`, `falsifiers_fired` | `findings.jsonl` | did the pre-registered instrument checks hold |
| program | `outcome` (§3.2) | `program/ledger.jsonl` | what did this produce for the program |

`verdict` is **not** derived from `gate_verdicts`. Deriving it would re-collapse
the vector this decision exists to un-collapse: a run can fail a gate and still
have observed something, and can pass every gate and still observe nothing.

**The instrument-failure case, stated because it is the one that binds.** A
pre-registered falsifier whose verdict is "instrument failure" (F1) takes ledger
`outcome: instrument-failed` — §3.2's definition, "the apparatus was shown **not**
to work; a method problem, not a phenomenon" — and its findings `verdict` is
`null`. This is not a new rule: it is the pairing G-E9 already enforces ("an
instrument that failed cannot carry a flagged phenomenon") and the precedent of
the #5-rerun record (DEC-023/024), which records an instrument indictment as
`verdict: null`.

**Divergence recorded, not silently propagated.** The committed #161 record
carries `verdict: flagged` with F1 fired. Under this section it should read
`verdict: null`. It is not changed here: `findings.jsonl` is append-only and gated
by G-E6, so a committed line is corrected by a new record or by the ledger
classification, never by an edit. #168 must not copy the `flagged` pairing into
the synthetic sample.

## 5. What step 2 (#168) must do

1. Add `"gate_verdicts"` and `"falsifiers_fired"` to `KNOWN_EXTENSIONS` in
   `tooling/gates/validate_findings.py`.
2. Add the two corresponding lines to the `findings.jsonl` header's "Extension
   keys" section (required by `test_findings_header_declares_every_extension_key`).
3. Commit a **synthetic** record carrying both keys with made-up values, per §2.
4. `python3 tooling/gates/run_all.py` exits 0; `python3 -m pytest
   tooling/gates/tests/ -k findings` passes.

**Explicitly out of scope for #168.** A *value-type* check — that `gate_verdicts`
is an object of booleans and `falsifiers_fired` a list of strings — is a gate
concern, not a registry concern. It is named here so it is not lost, and is filed
as its own task if wanted. G-E1's contract stays "declared keys only".

---

## References

- `docs/reference/COMPOSITION_PREREGISTRATION.md` §7 (falsifiers), §8 (gates) — the
  shape this decision must carry. On `main` via PR #157.
- `findings.jsonl` header — required keys and the "Extension keys" section.
- `tooling/gates/validate_findings.py` — `KNOWN_EXTENSIONS`, G-E1, G-E6.
- `docs/reference/PROGRAM_MANAGEMENT_SPEC.md` §3.2 (`outcome`), §4 (the ledger),
  §2 ("derive, never duplicate").
- `docs/reference/TEST_VALIDATION_SPEC.md` §7 layer 1 (mechanical schema checks).
- Issue #161 (the Phase 1 run whose record this shape replaces), #162 (the
  oversize parent), #168 / #169 (the rest of the chain), #25 (schema/header
  authority).
