"""Issue #153 (Rung-3 red-team step 3): execute the pre-registered variation grid.

Reimplemented from `docs/reference/REDTEAM_PREREGISTRATION.md` (the frozen grid
and outcome-table format) on top of the step-2 real-arm encoder
(`experiments/2026-10-19-rung3-redteam-step2.py`). Same arm, so the §4
independence constraint still holds: this file does not read or adapt
`experiments/2026-10-19-rung3-real-arm.py`, the #143-#145 probe, or any
#143-#145 results JSON. The corpus vocabulary is the shared DEC-011 generator
(`experiments/gen_cross_domain.py`), which is protocol input, not a run artifact.

Grid (REDTEAM_PREREGISTRATION.md §1): axes A x B x C x D at the frozen hook
= 3 x 2 x 2 x 3 = 36 cells, plus the frozen reference cell (seed 11), plus the
conditional layer-13 cell (§3).

  A  MIN_SUPPORT     in {3, 5, 10}   -- band lower-support floor, lo = MIN_SUPPORT/n
  B  CO_CHANCE_CAP   in {0.5, 0.7}   -- band upper cap, hi = sqrt(CO_CHANCE_CAP)
  C  firing rule     in {gt0, pct95}
  D  statistic seed  in {3, 17, 29}  -- permutation RNG; corpus frozen (see below)
  E  hook            blocks.12 (mandatory) + blocks.13 (conditional)

Axis D is the *statistic* seed only. §1 lists corpus construction (120/120,
zero shared tokenizer ids, carrier-wrapped, DEC-011) under "Protocol parameters
that are NOT varied", so the corpus is built once at CORPUS_SEED = 11 and every
cell reads the same encoded activations; only the permutation resample changes.

Interpretation note (axis A): §1 names MIN_SUPPORT as "the one free constant in
[the lo] rule", so it is varied *only* in the band rule. The pct95 binarizer's
minimum-positive guard stays at the frozen value 5, so axis A does not also
perturb the firing rule (axis C) -- §1: "a change in the result [is] attributable
to the varied axis."

Definition of done: every pre-registered cell is reported -- a results JSON in the
§6 outcome-table format with `best_z`, `cutoff`, `n_family`, `n_survivors` per
cell, no cell omitted.
"""
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_cross_domain import (ASTRO_ADJ, ASTRO_NOUN, ASTRO_VERB,  # noqa: E402,F401
                              COOK_ADJ, COOK_NOUN, COOK_VERB, astro_passage,
                              cook_passage)

MODEL_PATH = ("/home/openhands/.cache/huggingface/hub/models--unsloth--gemma-2-2b/"
              "snapshots/25319945f7fd83b8b903e12081777b7eef2ba993")
SAE_RELEASE = "gemma-scope-2b-pt-res-canonical"
DTYPE = torch.bfloat16

N_PER_DOMAIN = 120
CORPUS_SEED = 11          # frozen (protocol, §1)
BATCH = 32
N_PERM = 400
MIN_SUPPORT_VALUES = [3, 5, 10]      # axis A
CO_CHANCE_CAP_VALUES = [0.5, 0.7]    # axis B
FIRING_RULES = ["gt0", "pct95"]      # axis C
SEED_VALUES = [3, 17, 29]            # axis D (varied)
REF_SEED = 11                        # frozen reference cell
PCT_SUPPORT_GUARD = 5                # frozen; pct95 binarizer, not axis A

HOOK_LAYERS = [12, 13]               # axis E; 12 mandatory, 13 conditional
SAE_IDS = {12: "layer_12/width_16k/canonical",
           13: "layer_13/width_16k/canonical"}

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "2026-10-19-rung3-redteam-step3-results.json")


def build_corpus():
    import random
    rng = random.Random(CORPUS_SEED)
    cook = [cook_passage(rng) for _ in range(N_PER_DOMAIN)]
    astro = [astro_passage(rng) for _ in range(N_PER_DOMAIN)]
    return cook, astro


def encode(model, tok, saes, texts, layers):
    """One forward pass; encode each requested residual layer with its SAE.

    `blocks.<L>.hook_resid_post` = HF `hidden_states[L + 1]` (index 0 is the
    embedding output). TransformerLens 3.9.0 cannot load Gemma2, so the residual
    is read from the plain `transformers` forward pass instead (see step 2).
    """
    acc = {L: [] for L in layers}
    with torch.no_grad():
        for i in range(0, len(texts), BATCH):
            enc = tok(texts[i:i + BATCH], return_tensors="pt", padding=True)
            hs = model(**enc, output_hidden_states=True).hidden_states
            mask = enc["attention_mask"].bool()
            for L in layers:
                h = hs[L + 1]
                f = saes[L].encode(h.float().reshape(-1, h.shape[-1]))
                f = f.reshape(h.shape[0], h.shape[1], -1)
                f = f.masked_fill(~mask.unsqueeze(-1), float("-inf"))
                acc[L].append(f.amax(dim=1).float().cpu().numpy())
            del hs
    return {L: np.concatenate(acc[L], axis=0) for L in layers}


def binarize(fn, rule):
    if rule == "gt0":
        return fn > 0.0
    if rule.startswith("pct"):
        pct = int(rule[3:])
        thr = np.full(fn.shape[1], np.inf)
        for j in range(fn.shape[1]):
            pos = fn[:, j][fn[:, j] > 0]
            if pos.size >= PCT_SUPPORT_GUARD:
                thr[j] = np.percentile(pos, pct)
        return fn > thr[None, :]
    raise ValueError(rule)


def select_band(fa, fb, n, min_support, cap):
    """§2 band rule, with the two free constants supplied by the cell."""
    lo = min_support / n
    hi = float(np.sqrt(cap))
    ra, rb = fa.mean(axis=0), fb.mean(axis=0)
    return np.where((ra >= lo) & (ra <= hi) & (rb >= lo) & (rb <= hi))[0], lo, hi


def evaluate(bin_a, bin_b, sel, n, seed):
    A, B = bin_a[:, sel], bin_b[:, sel]
    obs = (A & B).mean(axis=0)
    rng = np.random.default_rng(seed)
    perm = np.empty((N_PERM, sel.size))
    for p in range(N_PERM):
        perm[p] = (A & B[rng.permutation(n)]).mean(axis=0)
    mu, sd = perm.mean(0), perm.std(0) + 1e-9
    z_obs = (obs - mu) / sd
    z_perm = (perm - mu) / sd
    cutoff = float(np.percentile(z_perm.max(axis=1), 95))
    surv = np.where(z_obs > cutoff)[0]
    top = int(np.argmax(z_obs))
    return {
        "n_family": int(sel.size),
        "best_z": float(z_obs.max()) if sel.size else float("nan"),
        "cutoff": cutoff,
        "n_survivors": int(surv.size),
        "survivor_ids": [int(sel[i]) for i in surv],
        "top_feature": int(sel[top]) if sel.size else None,
        "top_rate": float(obs[top]) if sel.size else None,
        "top_perm_mean": float(mu[top]) if sel.size else None,
    }


def cell_id(seed, sup, cap, rule, layer):
    return f"g-{seed}-{sup}-{cap:g}-{rule}-{layer}"


def main():
    from sae_lens import SAE

    print("=== issue #153: pre-registered variation grid ===")
    cook, astro = build_corpus()
    n = min(len(cook), len(astro))
    cook, astro = cook[:n], astro[:n]
    print(f"corpus: cooking={len(cook)} astronomy={len(astro)} (seed {CORPUS_SEED})")

    print("loading model (bf16, CPU)...")
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, dtype=DTYPE)
    model.eval()

    saes, hooks = {}, []
    for L in HOOK_LAYERS:
        try:
            saes[L] = SAE.from_pretrained(release=SAE_RELEASE,
                                          sae_id=SAE_IDS[L], device="cpu")
            hooks.append(L)
            print(f"  SAE layer {L} loaded: d_in={saes[L].cfg.d_in} "
                  f"d_sae={saes[L].cfg.d_sae} hook={saes[L].cfg.metadata.hook_name}")
        except Exception as e:  # noqa: BLE001 -- conditional cell (§3)
            print(f"  SAE layer {L} NOT available: {type(e).__name__}: {e}")

    print("encoding (one forward pass, all hooks)...")
    enc_c = encode(model, tok, saes, cook, hooks)
    enc_a = encode(model, tok, saes, astro, hooks)

    rows, notes = [], []
    ref = None
    for L in hooks:
        fc, fa = enc_c[L], enc_a[L]
        for rule in FIRING_RULES:
            bc, ba = binarize(fc, rule), binarize(fa, rule)
            for sup in MIN_SUPPORT_VALUES:
                for cap in CO_CHANCE_CAP_VALUES:
                    sel, lo, hi = select_band(bc, ba, n, sup, cap)
                    seeds = SEED_VALUES + ([REF_SEED] if (sup == 5 and cap == 0.5
                                                          and rule == "gt0"
                                                          and L == 12) else [])
                    for seed in seeds:
                        # §0: a cell that cannot run is reported, not dropped.
                        if sel.size < 2:
                            row = {"cell_id": cell_id(seed, sup, cap, rule, L),
                                   "seed": seed, "min_support": sup,
                                   "co_chance_cap": cap, "firing_rule": rule,
                                   "hook": f"blocks.{L}.hook_resid_post",
                                   "band": [lo, hi], "n_family": int(sel.size),
                                   "not_runnable": f"empty family (band lo="
                                   f"{lo:.4f} excludes all features under this rule)"}
                            rows.append(row)
                            print(f"  {row['cell_id']:<26} not_runnable: {row['not_runnable']}")
                            continue
                        r = evaluate(bc, ba, sel, n, seed)
                        row = {"cell_id": cell_id(seed, sup, cap, rule, L),
                               "seed": seed, "min_support": sup,
                               "co_chance_cap": cap, "firing_rule": rule,
                               "hook": f"blocks.{L}.hook_resid_post",
                               "band": [lo, hi], **r}
                        rows.append(row)
                        tag = " [REFERENCE]" if seed == REF_SEED else ""
                        print(f"  {row['cell_id']:<26} n_family={r['n_family']:<5} "
                              f"best_z={r['best_z']:.4f} cutoff={r['cutoff']:.4f} "
                              f"survivors={r['n_survivors']}{tag}")
                        if seed == REF_SEED:
                            ref = row

    if 13 not in hooks:
        notes.append("layer-13 cell not_runnable: release exposes no layer_13 "
                     "width_16k/canonical residual SAE")

    if ref is not None:
        print(f"\nreference check vs #145 (best_z=3.695, cutoff=4.664, 0 survivors): "
              f"best_z={ref['best_z']:.3f} cutoff={ref['cutoff']:.3f} "
              f"survivors={ref['n_survivors']}")

    total_survivors = sum(r.get("n_survivors", 0) for r in rows)
    survivors_any = [r["cell_id"] for r in rows if r.get("n_survivors", 0) > 0]
    decision = ("null SURVIVES (all cells 0 survivors)" if not survivors_any
                else f"null RE-OPENED -- survivors in {survivors_any}")

    out = {
        "run_id": os.environ.get("OH_RUN_ID", "20261019-1533-d9y9"),
        "issue": 153,
        "model": "unsloth/gemma-2-2b",
        "model_revision": "25319945f7fd83b8b903e12081777b7eef2ba993",
        "dtype": "bfloat16",
        "sae_release": SAE_RELEASE,
        "statistic": "standardized per-feature co-activation z",
        "null_model": f"pairing permutation, N_PERM={N_PERM}",
        "correction": "family-wise max-statistic (95th pct of max per-feature z)",
        "corpus": {"n_per_domain": N_PER_DOMAIN, "seed": CORPUS_SEED,
                   "varied": False},
        "axes": {"min_support": MIN_SUPPORT_VALUES,
                 "co_chance_cap": CO_CHANCE_CAP_VALUES,
                 "firing_rule": FIRING_RULES, "seed": SEED_VALUES,
                 "hook": [f"blocks.{L}.hook_resid_post" for L in hooks]},
        "reference_145": {"best_z": 3.695, "cutoff": 4.664, "n_survivors": 0},
        "reference_cell": ref,
        "n_cells": len(rows),
        "n_cells_with_survivors": len(survivors_any),
        "decision": decision,
        "notes": notes,
        "cells": rows,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n=== decision: {decision} ===")
    print(f"cells={len(rows)}  with_survivors={len(survivors_any)}  "
          f"total_survivors={total_survivors}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
