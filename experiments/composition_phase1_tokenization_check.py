"""Tokenization precondition for the composition-emergence Phase 1 probe.

Pre-registration §3: "verify that each composite's target span tokenizes as the
concatenation of its constituents' tokenizations in the carrier. A pair failing
this check is excluded and recorded."

This is a *precondition on reading*, not a gate on running — tokenizer only, no
SAE, no forward passes (method constraint in issue #160).

**Tokenizer:** EleutherAI/pythia-70m-deduped (the authorized target).
**Issue:** ephapse #160 (step 2/3 of the #158 decomposition; DEC-043).
**Word lists:** experiments/composition_phase1_word_lists.json, transcribed
verbatim from the pre-registration Appendix A (PR #157 branch) because the
pre-registration is not yet on `main`.

Check definition
----------------
For a composite `A B` placed at TARGET in a carrier `prefix + TARGET + suffix`:

    span(prefix + "A B" + suffix)  ==  span(prefix + "A" + suffix)
                                    + span(prefix + "B" + suffix)

where `span(...)` is the set of token ids whose character offsets overlap the
replaced text (so a leading-space token like `` herring`` is included). The
composite fails when the two differ — i.e. the boundary between the constituents
produced a token that neither constituent produces alone, which would make a
"new" feature a tokenization artifact.

A pair passes only if it passes in every carrier of its arm.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TOKENIZER_ID = "EleutherAI/pythia-70m-deduped"
HERE = Path(__file__).resolve().parent
LISTS = HERE / "composition_phase1_word_lists.json"


def span_ids(tok, text: str, sub: str) -> list[int]:
    """Token ids whose character offsets overlap `sub` within `text`."""
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    ids = enc["input_ids"]
    offsets = enc["offset_mapping"]
    start = text.index(sub)
    end = start + len(sub)
    return [i for i, (a, b) in zip(ids, offsets) if a < end and b > start]


def check_pair(tok, composite: str, carrier: str) -> tuple[bool, list[int], list[int]]:
    a, b = composite.split(" ", 1)
    prefix, suffix = carrier.split("TARGET")
    full = span_ids(tok, f"{prefix}{composite}{suffix}", composite)
    left = span_ids(tok, f"{prefix}{a}{suffix}", a)
    right = span_ids(tok, f"{prefix}{b}{suffix}", b)
    return full == left + right, full, left + right


def main() -> int:
    from transformers import AutoTokenizer

    data = json.loads(LISTS.read_text())
    tok = AutoTokenizer.from_pretrained(TOKENIZER_ID)

    print(f"tokenizer: {TOKENIZER_ID}  vocab={tok.vocab_size}")
    print(f"word lists: {LISTS.name} (source: {data['_source']})")
    print()

    composites: list[tuple[str, str, str]] = []  # (arm, composite, carrier)
    for arm, items in data["adj_noun"].items():
        for composite in items:
            for carrier in data["carriers"]["adj_noun"]:
                composites.append((arm, composite, carrier))
    for composite in data["verb_object"]["verb_object"]:
        for carrier in data["carriers"]["verb_object"]:
            composites.append(("verb_object", composite, carrier))

    # A pair passes only if it passes in every carrier of its arm.
    pair_status: dict[tuple[str, str], bool] = {}
    failures: list[tuple[str, str, str, list[int], list[int]]] = []
    for arm, composite, carrier in composites:
        ok, got, want = check_pair(tok, composite, carrier)
        key = (arm, composite)
        pair_status[key] = pair_status.get(key, True) and ok
        if not ok:
            failures.append((arm, composite, carrier, got, want))

    pairs = sorted(pair_status)
    n_pass = sum(1 for p in pairs if pair_status[p])
    n_fail = len(pairs) - n_pass

    print("=== summary ===")
    print(
        f"checked={len(pairs)} pass={n_pass} fail={n_fail} "
        f"(carrier-instances={len(composites)}; "
        f"tokenizer={TOKENIZER_ID})"
    )
    if failures:
        print()
        print("=== failing pairs (excluded and recorded) ===")
        for arm, composite, carrier, got, want in failures:
            print(f"  [{arm}] {composite!r} in {carrier!r}")
            print(f"      composite span = {got}")
            print(f"      concat(A)+concat(B) = {want}")

    syn = data["synonym_pairs"]
    print()
    print(
        f"synonym_pairs={len(syn)} (single-word pairs; no constituent "
        "concatenation to verify — not applicable to the precondition)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
