"""Issue #143 (rung 3, step 1): rung-3 probe harness + selectivity band.

**Model:** `unsloth/gemma-2-2b` (public mirror of the gated `google/gemma-2-2b`;
  the gated official checkpoint needs an `HF_TOKEN` this sandbox lacks — #39).
  bf16 weights, fp32 SAE, CPU.
**SAE:** `gemma-scope-2b-pt-res-canonical`, `layer_12/width_16k/canonical`,
  hook `blocks.12.hook_resid_post` (d_in=2304, d_sae=16384).
**Inputs:** `Corpus/cross_domain.json` — 120 cooking / 120 astronomy passages,
  zero shared tokenizer ids (DEC-011). Regenerated here with the gemma tokenizer
  used for the disjointness check.
**Question (step 1 only):** adapt the rung-2 probe to the frozen rung-3
  parameters, load model + SAE, and derive the §2 selectivity band `[lo, hi]`
  from the measured per-domain firing-rate histogram.
**Scope:** this script stops at the band. The positive control (#144) and the
  real cross-domain arm (#145) are separate, blocked steps.
**Correction / null:** none run here — this step measures a distribution and
  derives a band. No parameter is chosen after seeing the data (DEC-005).
**Issue:** #143 (run 20261019-0040-urtt).

The §2 rule is re-derived, not copied (§0/§2 of RUNG3_PREREGISTRATION.md):

  lo = the smallest firing rate whose expected firing count supports the
       10 %-prevalent plant. Operationalised as the smallest observed rate
       whose count over the 120 passages is >= MIN_SUPPORT (5) — the same
       minimum-support constant the rung-2 `binarize()` uses before it will
       trust a per-feature percentile. At n=120 this lands at ~0.04-0.05,
       reproducing the 70M reference `lo=0.05` from the rule rather than by
       copying it.
  hi = the largest firing rate whose chance (permutation-null) co-activation
       stays below 0.5. Under a pairing permutation the null co-activation of
       two independent features is the product of their marginal firing rates,
       so the conservative equal-marginal bound is `r * r <= 0.5`, i.e.
       `hi = sqrt(0.5)`. `hi` is also capped at the largest rate actually
       present in the histogram.

The band is applied in BOTH domains (family = features inside `[lo, hi]` in
cooking *and* astronomy), matching rung 2 (DEC-024).
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
N_PERM = 400                                   # frozen; not exercised in step 1
PLANT_RATE = 0.10                              # frozen; the plant prevalence
MIN_SUPPORT = 5                                # rung-2 minimum support constant
CO_CHANCE_CAP = 0.5                            # §2 upper-bound cap on null co-activation
N_PER_DOMAIN = 120
SEED = 11

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "Corpus", "cross_domain.json")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "2026-10-19-rung3-probe-results.json")

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
    la = [len(tok.encode(t, add_special_tokens=False)) for t in cook]
    lb = [len(tok.encode(t, add_special_tokens=False)) for t in astro]
    print(f"CORPUS {len(cook)} cooking / {len(astro)} astronomy; "
          f"0 shared tokenizer ids (gemma tokenizer, add_special_tokens=False)")
    print(f"  median tokens: cooking {sorted(la)[len(la) // 2]} "
          f"astronomy {sorted(lb)[len(lb) // 2]}")
    return cook, astro


@torch.no_grad()
def encode(model, sae, tok, texts, batch=16):
    """Per-passage max SAE activation. Padded batches, masked to real tokens."""
    feats = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        enc = tok(chunk, return_tensors="pt", padding=True)
        out = model(**enc, output_hidden_states=True)
        # hidden_states[0] is the embedding output; hidden_states[LAYER+1] is the
        # output of block LAYER, i.e. hook_resid_post of that block.
        resid = out.hidden_states[LAYER + 1].float()
        mask = enc["attention_mask"].bool()
        f = sae.encode(resid.reshape(-1, resid.shape[-1]))
        f = f.reshape(resid.shape[0], resid.shape[1], -1)
        f = f.masked_fill(~mask.unsqueeze(-1), float("-inf"))
        feats.append(f.amax(dim=1).cpu().numpy())
    return np.concatenate(feats, axis=0)


def derive_band(hist_rates, n_passages):
    """§2 rule, re-derived from the histogram (see module docstring)."""
    support = hist_rates * n_passages
    lo_candidates = hist_rates[support >= MIN_SUPPORT]
    lo = float(lo_candidates.min()) if lo_candidates.size else float(hist_rates.max())
    hi_bound = float(np.sqrt(CO_CHANCE_CAP))
    hi_present = float(hist_rates.max())
    hi = min(hi_bound, hi_present)
    return lo, hi


def main():
    print("=== #143 rung-3 step 1: harness + selectivity band ===")
    model, tok = load_model()
    cook, astro = build_corpus(tok)

    from sae_lens import SAE
    t0 = time.time()
    sae = SAE.from_pretrained(release=SAE_RELEASE, sae_id=SAE_ID, device="cpu")
    print(f"SAE {SAE_RELEASE} / {SAE_ID} loaded wall={time.time() - t0:.1f}s "
          f"d_in={sae.cfg.d_in} d_sae={sae.cfg.d_sae} "
          f"hook={sae.cfg.metadata.hook_name}")

    t0 = time.time()
    fc = encode(model, sae, tok, cook)
    fa = encode(model, sae, tok, astro)
    print(f"encoded {len(cook)}+{len(astro)} passages in {time.time() - t0:.1f}s; "
          f"peak_rss={rss_gb():.2f} GB")

    # Per-domain firing rates under the primary `gt0` rule (DEC-027).
    rc, ra = (fc > 0).mean(axis=0), (fa > 0).mean(axis=0)
    # Histogram over the union of nonzero rates (both domains), 50 bins on [0,1].
    all_rates = np.concatenate([rc, ra])
    hist, edges = np.histogram(all_rates, bins=50, range=(0.0, 1.0))

    lo, hi = derive_band(all_rates[all_rates > 0], N_PER_DOMAIN)
    sel = np.where((rc >= lo) & (rc <= hi) & (ra >= lo) & (ra <= hi))[0]

    print(f"\n--- derived selectivity band ---")
    print(f"  lo={lo:.4f}  hi={hi:.4f}  |family|={sel.size} "
          f"(of {fc.shape[1]} features)")
    print(f"  firing features: cooking {int((rc > 0).sum())} "
          f"astronomy {int((ra > 0).sum())}")

    results = {
        "run_id": "20261019-0040-urtt", "issue": 143, "step": "rung3-step1",
        "model": MIRROR, "model_official": MODEL_OFFICIAL,
        "model_revision": MIRROR_REVISION,
        "checkpoint_note": "public mirror; gated official checkpoint needs HF_TOKEN",
        "dtype": str(DTYPE), "device": "cpu",
        "sae": {"release": SAE_RELEASE, "sae_id": SAE_ID, "hook": HOOK,
                "d_in": int(sae.cfg.d_in), "d_sae": int(sae.cfg.d_sae)},
        "corpus": {"n_per_domain": N_PER_DOMAIN, "seed": SEED,
                   "token_disjoint": True, "median_tokens": None},
        "firing_rule": "gt0",
        "histogram": {"bin_edges": edges.tolist(), "counts": hist.tolist()},
        "band": {"lo": lo, "hi": hi, "family_size": int(sel.size),
                 "lo_rule": f"smallest rate with count >= {MIN_SUPPORT} over "
                            f"{N_PER_DOMAIN} passages",
                 "hi_rule": f"min(sqrt({CO_CHANCE_CAP}), max observed rate)",
                 "family_definition": "inside [lo,hi] in BOTH domains"},
        "n_firing_features": {"cooking": int((rc > 0).sum()),
                              "astronomy": int((ra > 0).sum())},
        "transfer_table_note": "band newly derived (§0/§2); not copied from 70M",
    }
    with open(OUT, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
