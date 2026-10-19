"""Issue #145 (rung 3, step 3): the real cross-domain arm at gemma-2-2b.

**Model:** `unsloth/gemma-2-2b` (public mirror of the gated `google/gemma-2-2b`;
  the gated official checkpoint needs an `HF_TOKEN` this sandbox lacks — #39).
  bf16 weights, fp32 SAE, CPU.
**Inputs:** `Corpus/cross_domain.json` — 120 cooking / 120 astronomy passages,
  regenerated with the gemma tokenizer, zero shared tokenizer ids (DEC-011),
  identical to steps 1 (#143) and 2 (#144).
**Question:** with no injection, does any SAE feature at
  `blocks.12.hook_resid_post` co-activate across the two token-disjoint domains
  more than the permutation null predicts?
**Null:** pairing permutation, N_PERM=400 — each feature's matched-pairing
  co-activation rate is standardized against its own mean/sd over shuffled
  pairings (the rung-2 statistic, DEC-019/DEC-027).
**Correction:** family-wise max-statistic on the standardized statistic: the
  95th percentile, over permutations, of the maximum per-feature z (DEC-016).
  BH-FDR not used.
**Firing rule:** `gt0` (positive activation) primary; `pct95` reported secondary.
**Issue:** #145.

Runs only after the step-2 positive control recovered (it did: verdict
`recovered`, run 20261019-0101-05fv). A null here is a null *of the SAE
instrument at 2B*; the comparator cross-cut is untested at rung-3 scale
(DEC-034), so the scale explanation is not retired.

GATE-DECL
{
  "statistic": {
    "name": "standardized per-feature cross-domain co-activation z (permutation-null)",
    "family": "binary-marginal co-activation rate, standardized",
    "threshold": "family-wise 95th pct of max per-feature z over permutations",
    "n_perm": 400,
    "note": "not the NPMI family; G-C1 decides NPMI/catch-all exactly and flags this family for review rather than passing silently"
  },
  "control": {
    "plant_token": "Zorblat",
    "plant_rate": 0.10,
    "grid": [0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40],
    "computes_planted_presence": false,
    "records_both_groups": false,
    "note": "the control is step 2 (#144, run 20261019-0101-05fv), which recovered; this arm is the real no-injection run and computes no planted presence"
  },
  "readings": [
    {"name": "n_family", "depends_on_effect": false},
    {"name": "best_z_vs_cutoff", "depends_on_effect": false},
    {"name": "n_survivors", "depends_on_effect": true}
  ],
  "comparability": {
    "model": "unsloth/gemma-2-2b",
    "hook": "blocks.12.hook_resid_post",
    "threshold": "family-wise 95th pct max-z over 400 permutations",
    "n": 120,
    "correction": "family-wise max-statistic, no BH-FDR"
  },
  "tests": []
}
END-GATE-DECL
"""
import json
import os
import sys
import time

import numpy as np
import torch

# --- frozen rung-3 parameters (RUNG3_PREREGISTRATION.md) -------------------
MIRROR = os.environ.get("EPHAPSE_GEMMA_MIRROR", "unsloth/gemma-2-2b")
MIRROR_REVISION = "25319945f7fd83b8b903e12081777b7eef2ba993"
MODEL_OFFICIAL = "google/gemma-2-2b"          # gated; recorded for provenance
SAE_RELEASE = "gemma-scope-2b-pt-res-canonical"
SAE_ID = "layer_12/width_16k/canonical"
HOOK = "blocks.12.hook_resid_post"
LAYER = 12
DTYPE = torch.bfloat16
N_PERM = 400
N_PER_DOMAIN = 120
SEED = 11
MIN_SUPPORT = 5
CO_CHANCE_CAP = 0.5

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "2026-10-19-rung3-real-arm-results.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_cross_domain import astro_passage, cook_passage  # noqa: E402


def rss_gb():
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6


def load_model():
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MIRROR, revision=MIRROR_REVISION)
    model = AutoModelForCausalLM.from_pretrained(
        MIRROR, revision=MIRROR_REVISION, dtype=DTYPE)
    model.eval()
    n_params = sum(p.numel() for p in model.parameters())
    cfg = model.config
    print(f"MODEL {MIRROR} (mirror of gated {MODEL_OFFICIAL})")
    print(f"  loaded wall={time.time() - t0:.1f}s params={n_params / 1e9:.3f}B "
          f"n_layers={cfg.num_hidden_layers} d_model={cfg.hidden_size} "
          f"d_vocab={cfg.vocab_size}")
    print(f"  dtype={DTYPE} peak_rss={rss_gb():.2f} GB")
    return model, tok


def build_corpus(tok):
    import random

    rng = random.Random(SEED)
    cook = [cook_passage(rng) for _ in range(N_PER_DOMAIN)]
    astro = [astro_passage(rng) for _ in range(N_PER_DOMAIN)]

    def ids(s):
        return set(tok.encode(s, add_special_tokens=False))

    viol = [(i, sorted(ids(a) & ids(b)))
            for i, (a, b) in enumerate(zip(cook, astro))
            if ids(a) & ids(b)]
    if viol:
        raise SystemExit(f"DEC-011 input gate violated: {len(viol)} shared-id "
                         f"pairs (first {viol[:3]})")
    med = int(np.median([len(ids(s)) for s in cook + astro]))
    print(f"CORPUS {len(cook)} cooking / {len(astro)} astronomy; "
          f"0 shared tokenizer ids (gemma tokenizer, add_special_tokens=False); "
          f"median_tokens={med}")
    return cook, astro, med


@torch.no_grad()
def encode(model, sae, tok, texts, batch=16):
    """Per-passage max SAE activation. Padded batches, masked to real tokens."""
    feats = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        enc = tok(chunk, return_tensors="pt", padding=True)
        out = model(**enc, output_hidden_states=True)
        # hidden_states[LAYER + 1] is the output of block LAYER, i.e.
        # hook_resid_post of that block.
        resid = out.hidden_states[LAYER + 1].float()
        mask = enc["attention_mask"].bool()
        f = sae.encode(resid.reshape(-1, resid.shape[-1]))
        f = f.reshape(resid.shape[0], resid.shape[1], -1)
        f = f.masked_fill(~mask.unsqueeze(-1), float("-inf"))
        feats.append(f.amax(dim=1).cpu().numpy())
    return np.concatenate(feats, axis=0)


def binarize(fn, rule="gt0"):
    """Firing definition (DEC-023). `gt0` primary; `pct{K}` secondary."""
    if rule == "gt0":
        return fn > 0.0
    if rule.startswith("pct"):
        pct = int(rule[3:])
        d = fn.shape[1]
        thr = np.full(d, np.inf)
        for j in range(d):
            pos = fn[:, j][fn[:, j] > 0]
            if pos.size >= 5:
                thr[j] = np.percentile(pos, pct)
        return fn > thr[None, :]
    raise ValueError(rule)


def derive_band(hist_rates, n_passages):
    """§2 rule, re-derived from the histogram (see module docstring)."""
    support = hist_rates * n_passages
    lo_candidates = hist_rates[support >= MIN_SUPPORT]
    lo = float(lo_candidates.min()) if lo_candidates.size else float(hist_rates.max())
    hi_bound = float(np.sqrt(CO_CHANCE_CAP))
    hi_present = float(hist_rates.max())
    hi = min(hi_bound, hi_present)
    return lo, hi


def evaluate(bin_a, bin_b, sel, n, rng):
    """Standardized per-feature co-activation z, family-wise max-statistic."""
    A, B = bin_a[:, sel], bin_b[:, sel]
    obs = (A & B).mean(axis=0)
    perm = np.empty((N_PERM, sel.size))
    for p in range(N_PERM):
        perm[p] = (A & B[rng.permutation(n)]).mean(axis=0)
    mu, sd = perm.mean(0), perm.std(0) + 1e-9
    z_obs = (obs - mu) / sd
    z_perm = (perm - mu) / sd
    cutoff = float(np.percentile(z_perm.max(axis=1), 95))
    best_i = int(np.argmax(z_obs))
    surv = np.where(z_obs > cutoff)[0]
    return {
        "n_family": int(sel.size),
        "best_z": float(z_obs.max()), "cutoff_z": cutoff,
        "n_survivors": int(surv.size),
        "survivor_features": [int(sel[i]) for i in surv],
        "survivor_rates": [float(obs[i]) for i in surv],
        "survivor_rates_perm_mean": [float(mu[i]) for i in surv],
        "top_feature": int(sel[best_i]),
        "top_rate": float(obs[best_i]), "top_perm_mean": float(mu[best_i]),
    }


def main():
    print("=== #145 rung-3 step 3: real cross-domain arm ===")
    model, tok = load_model()
    cook, astro, med = build_corpus(tok)
    n = min(len(cook), len(astro))

    from sae_lens import SAE
    t0 = time.time()
    sae = SAE.from_pretrained(release=SAE_RELEASE, sae_id=SAE_ID, device="cpu")
    print(f"SAE {SAE_RELEASE} / {SAE_ID} loaded wall={time.time() - t0:.1f}s "
          f"d_in={sae.cfg.d_in} d_sae={sae.cfg.d_sae} "
          f"hook={sae.cfg.metadata.hook_name}")

    cache = OUT.replace(".json", "-acts.npz")
    t0 = time.time()
    if os.path.exists(cache):
        z = np.load(cache)
        fc, fa = z["fc"], z["fa"]
        print(f"loaded cached activations from {cache}")
    else:
        fc = encode(model, sae, tok, cook)
        fa = encode(model, sae, tok, astro)
        np.savez_compressed(cache, fc=fc, fa=fa)
    print(f"encoded {len(cook)}+{len(astro)} passages in {time.time() - t0:.1f}s; "
          f"peak_rss={rss_gb():.2f} GB")

    # ---- band, re-derived from the measured firing distribution ----
    rc, ra = (fc > 0).mean(axis=0), (fa > 0).mean(axis=0)
    all_rates = np.concatenate([rc, ra])
    lo, hi = derive_band(all_rates[all_rates > 0], N_PER_DOMAIN)
    print(f"selectivity band: lo={lo:.4f} hi={hi:.4f}")

    results = {"rules": {}}
    for rule in ("gt0", "pct95"):
        bc, ba = binarize(fc, rule), binarize(fa, rule)
        sel = np.where((bc.mean(0) >= lo) & (bc.mean(0) <= hi) &
                       (ba.mean(0) >= lo) & (ba.mean(0) <= hi))[0]
        if sel.size < 2:
            results["rules"][rule] = {"n_family": int(sel.size),
                                      "n_survivors": 0,
                                      "note": "no features in the band"}
            print(f"  rule={rule:<6} |family|={sel.size} (too small)")
            continue
        r = evaluate(bc, ba, sel, n, np.random.default_rng(SEED))
        results["rules"][rule] = r
        print(f"  rule={rule:<6} |family|={r['n_family']:<5} "
              f"best_z={r['best_z']:6.2f} cutoff={r['cutoff_z']:5.2f} "
              f"survivors={r['n_survivors']}")

    gt0 = results["rules"].get("gt0", {})
    survivors = int(gt0.get("n_survivors", 0))
    if "note" in gt0:
        verdict = "empty-family"
    elif survivors > 0:
        verdict = "survivors"
    else:
        verdict = "null"

    print(f"\n=== summary ===\n  family={gt0.get('n_family')} "
          f"survivors={survivors} best_z={gt0.get('best_z')} "
          f"cutoff={gt0.get('cutoff_z')}\n  verdict: {verdict}")

    out = {
        "run_id": "20261019-0501-ccdw", "issue": 145, "step": "rung3-step3",
        "model": MIRROR, "model_official": MODEL_OFFICIAL,
        "model_revision": MIRROR_REVISION,
        "checkpoint_note": "public mirror; gated official checkpoint needs HF_TOKEN (#39)",
        "dtype": str(DTYPE), "device": "cpu",
        "sae": {"release": SAE_RELEASE, "sae_id": SAE_ID, "hook": HOOK,
                "d_in": int(sae.cfg.d_in), "d_sae": int(sae.cfg.d_sae)},
        "corpus": {"n_per_domain": n, "seed": SEED, "token_disjoint": True,
                   "median_tokens": med},
        "firing_rule": "gt0",
        "band": {"lo": lo, "hi": hi,
                 "note": "re-derived from the same corpus; steps 1/2 reported "
                         "[0.0417, 0.7071]"},
        "statistic": "standardized per-feature cross-domain co-activation z",
        "null_model": f"pairing permutation, N_PERM={N_PERM}",
        "correction": "family-wise max-statistic on the standardized statistic "
                      "(95th pct over permutations of max per-feature z)",
        "control": {"step": 2, "issue": 144, "run_id": "20261019-0101-05fv",
                    "verdict": "recovered",
                    "note": "the positive control recovered before this arm was read"},
        "rules": results["rules"],
        "verdict": verdict,
        "verdict_caveat": "a null here is a null of the SAE instrument at 2B; the "
                          "comparator cross-cut (DEC-034) is untested at rung-3 "
                          "scale, so the scale explanation is not retired",
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
