"""Issue #152 (Rung-3 red-team step 2): independent reimplementation of the
real-arm analysis.

Reimplemented from `docs/reference/RUNG3_PREREGISTRATION.md` ALONE, per the
REDTEAM_PREREGISTRATION.md §4 independence constraint: this file does not read or
adapt `experiments/2026-10-19-rung3-real-arm.py`, the #143-#145 probe, or any
#143-#145 results JSON. The corpus vocabulary is the shared DEC-011 generator
(`experiments/gen_cross_domain.py`), which is protocol input, not a run artifact.

Frozen config (REDTEAM_PREREGISTRATION.md §0/§1, seed axis D reference = 11):
  model   unsloth/gemma-2-2b @ 25319945f7fd83b8b903e12081777b7eef2ba993, bf16, CPU
  SAE     gemma-scope-2b-pt-res-canonical, layer_12/width_16k/canonical
  hook    blocks.12.hook_resid_post
  stat    z = (obs_rate - perm_mean) / perm_sd, per family feature
  cutoff  95th pct over permutations of max per-feature z
  N_PERM  400
  rule    gt0 (primary), pct95 (secondary)
  band    re-derived per §2: lo = MIN_SUPPORT / n; hi = sqrt(CO_CHANCE_CAP)
          (MIN_SUPPORT=5, CO_CHANCE_CAP=0.5 frozen)

Definition of done: runs to completion, writes a results JSON with family size,
best-z, cutoff, and survivor count for the frozen config at seed 11.
"""
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_cross_domain import (ASTRO_ADJ, ASTRO_NOUN, ASTRO_VERB,  # noqa: E402
                              COOK_ADJ, COOK_NOUN, COOK_VERB, astro_passage,
                              cook_passage)

MODEL_PATH = ("/home/openhands/.cache/huggingface/hub/models--unsloth--gemma-2-2b/"
              "snapshots/25319945f7fd83b8b903e12081777b7eef2ba993")
SAE_RELEASE = "gemma-scope-2b-pt-res-canonical"
SAE_ID = "layer_12/width_16k/canonical"
HOOK = "blocks.12.hook_resid_post"
DTYPE = torch.bfloat16

N_PER_DOMAIN = 120
CORPUS_SEED = 11          # gen_cross_domain.py SEED
SEED = 11                 # statistic seed, axis D reference (frozen config)
BATCH = 32
N_PERM = 400
MIN_SUPPORT = 5           # axis A frozen value
CO_CHANCE_CAP = 0.5       # axis B frozen value
PLANT_TOKEN = "Zorblat"
PLANT_RATE = 0.10

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "2026-10-19-rung3-redteam-step2-results.json")


def build_corpus():
    import random
    rng = random.Random(CORPUS_SEED)
    cook = [cook_passage(rng) for _ in range(N_PER_DOMAIN)]
    astro = [astro_passage(rng) for _ in range(N_PER_DOMAIN)]
    return cook, astro


def encode(model, sae, texts):
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), BATCH):
            _, c = model.run_with_cache(texts[i:i + BATCH],
                                        names_filter=lambda n: n == HOOK)
            out.append(sae.encode(c[HOOK]).amax(dim=1).float().cpu().numpy())
            del c
    return np.concatenate(out, axis=0)


def binarize(fn, rule):
    if rule == "gt0":
        return fn > 0.0
    if rule.startswith("pct"):
        pct = int(rule[3:])
        thr = np.full(fn.shape[1], np.inf)
        for j in range(fn.shape[1]):
            pos = fn[:, j][fn[:, j] > 0]
            if pos.size >= MIN_SUPPORT:
                thr[j] = np.percentile(pos, pct)
        return fn > thr[None, :]
    raise ValueError(rule)


def select_band(fa, fb, n):
    """§2 band rule. lo = smallest rate whose passage-support carries a
    10 %-prevalent plant: MIN_SUPPORT passages out of n. hi = rate above which
    the feature's permutation-null (chance) co-activation exceeds CO_CHANCE_CAP;
    for a feature firing at rate r in both domains the chance co-activation is
    r*r, so hi = sqrt(CO_CHANCE_CAP)."""
    lo = MIN_SUPPORT / n
    hi = float(np.sqrt(CO_CHANCE_CAP))
    ra, rb = fa.mean(axis=0), fb.mean(axis=0)
    return np.where((ra >= lo) & (ra <= hi) & (rb >= lo) & (rb <= hi))[0], lo, hi


def evaluate(bin_a, bin_b, sel, n):
    A, B = bin_a[:, sel], bin_b[:, sel]
    obs = (A & B).mean(axis=0)
    rng = np.random.default_rng(SEED)
    perm = np.empty((N_PERM, sel.size))
    for p in range(N_PERM):
        perm[p] = (A & B[rng.permutation(n)]).mean(axis=0)
    mu, sd = perm.mean(0), perm.std(0) + 1e-9
    z_obs = (obs - mu) / sd
    z_perm = (perm - mu) / sd
    cutoff = float(np.percentile(z_perm.max(axis=1), 95))
    surv = np.where(z_obs > cutoff)[0]
    return {
        "n_family": int(sel.size),
        "best_z": float(z_obs.max()),
        "cutoff_z": cutoff,
        "n_survivors": int(surv.size),
        "survivor_features": [int(sel[i]) for i in surv],
        "top_feature": int(sel[int(np.argmax(z_obs))]),
        "top_rate": float(obs[int(np.argmax(z_obs))]),
        "top_perm_mean": float(mu[int(np.argmax(z_obs))]),
        "raw_best_rate": float(obs.max()),
        "raw_cutoff": float(np.percentile(perm.max(axis=1), 95)),
    }


def main():
    from sae_lens import SAE
    from transformer_lens import HookedTransformer

    print("=== issue #152: independent real-arm reimplementation ===")
    cook, astro = build_corpus()
    n = min(len(cook), len(astro))
    cook, astro = cook[:n], astro[:n]
    print(f"corpus: cooking={len(cook)} astronomy={len(astro)}")

    print("loading model (bf16, CPU)...")
    model = HookedTransformer.from_pretrained(MODEL_PATH, device="cpu",
                                              dtype=DTYPE)
    model.eval()
    print("loading SAE...")
    sae = SAE.from_pretrained(release=SAE_RELEASE, sae_id=SAE_ID, device="cpu")
    print(f"  d_in={sae.cfg.d_in} d_sae={sae.cfg.d_sae} "
          f"hook={sae.cfg.metadata.hook_name}")

    print("encoding cooking...")
    fc = encode(model, sae, cook)
    print("encoding astronomy...")
    fa = encode(model, sae, astro)

    results = {}
    for rule in ("gt0", "pct95"):
        bc, ba = binarize(fc, rule), binarize(fa, rule)
        sel, lo, hi = select_band(bc, ba, n)
        print(f"\n[rule={rule}] band=[{lo:.4f},{hi:.4f}] |family|={sel.size}")
        if sel.size < 2:
            results[rule] = {"n_family": int(sel.size), "note": "no family"}
            continue
        r = evaluate(bc, ba, sel, n)
        r["band"] = [lo, hi]
        results[rule] = r
        print(f"  best_z={r['best_z']:.3f} cutoff={r['cutoff_z']:.3f} "
              f"survivors={r['n_survivors']}")

    g = results.get("gt0", {})
    print("\n=== summary (gt0, frozen config) ===")
    print(f"  |family|={g.get('n_family')}  best_z={g.get('best_z')}  "
          f"cutoff={g.get('cutoff_z')}  survivors={g.get('n_survivors')}")
    print(f"  #145 reference: best_z=3.695 cutoff=4.664 survivors=0")

    out = {
        "run_id": "20261019-1120-eph2",
        "issue": 152,
        "model": "unsloth/gemma-2-2b",
        "model_revision": "25319945f7fd83b8b903e12081777b7eef2ba993",
        "dtype": "bfloat16",
        "sae": SAE_ID,
        "sae_release": SAE_RELEASE,
        "hook": HOOK,
        "corpus": {"n_per_domain": n, "seed": CORPUS_SEED},
        "statistic": "standardized per-feature co-activation z",
        "null_model": f"pairing permutation, N_PERM={N_PERM}",
        "correction": "family-wise max-statistic (95th pct of max per-feature z)",
        "seed": SEED,
        "min_support": MIN_SUPPORT,
        "co_chance_cap": CO_CHANCE_CAP,
        "band_rule": "lo=MIN_SUPPORT/n; hi=sqrt(CO_CHANCE_CAP)",
        "reference_145": {"best_z": 3.695, "cutoff": 4.664, "n_survivors": 0},
        "real": results,
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
