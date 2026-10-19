"""Issue #144 (rung 3, step 2): frozen positive control at gemma-2-2b.

**Model:** `unsloth/gemma-2-2b` (public mirror of the gated `google/gemma-2-2b`;
  the gated official checkpoint needs an `HF_TOKEN` this sandbox lacks — #39).
  bf16 weights, fp32 SAE, CPU.
**Inputs:** `Corpus/cross_domain.json` — 120 cooking / 120 astronomy passages,
  regenerated with the gemma tokenizer, zero shared tokenizer ids (DEC-011),
  identical to step 1 (#143) so the control is comparable to the real arm.
**Question:** does the frozen rung-3 statistic recover a planted feature when
  `PLANT_TOKEN = "Zorblat"` is appended to `PLANT_RATE` of the paired passages in
  BOTH domains, across the frozen injection grid?
**Null:** pairing permutation, N_PERM=400 — each feature's matched-pairing
  co-activation rate is standardized against its own mean/sd over shuffled
  pairings (the rung-2 statistic, DEC-019/DEC-027).
**Correction:** family-wise max-statistic on the standardized statistic: the
  95th percentile, over permutations, of the maximum per-feature z (DEC-016).
  BH-FDR not used.
**Issue:** #144 (run 20261019-0101-05fv).

Runs BEFORE the real cross-domain arm is read (the rung-2 rule; DEC-019). The
control must be shown constructible — the plant raises the target feature's
activation in BOTH domains — before recovery is interpreted. The frozen grid is
`rate ∈ [0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40]`; the recovery
curve is a result, not a single chosen rate.

Construction is exact and cheap: the token is APPENDED to the passage, so a
planted passage's max SAE activation is identical to the same passage with the
token appended (max is monotone under appending — the earlier tokens are
unchanged and the appended token only adds one). The grid is therefore realised
by encoding each clean passage once and each would-be-planted passage once, then
mixing per rate, rather than re-encoding 9 times.

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
    "computes_planted_presence": true,
    "records_both_groups": true,
    "note": "mean(activation | injected) - mean(activation | not injected) recorded per domain at every grid rate, before recovery is read (DEC-019)"
  },
  "readings": [
    {"name": "constructibility_margin_per_domain", "depends_on_effect": true},
    {"name": "planted_feature_z_vs_cutoff", "depends_on_effect": true},
    {"name": "recovered_rate", "gated_by": "constructibility_margin_per_domain > 0 in both domains"}
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
PLANT_TOKEN = "Zorblat"
PLANT_RATE = 0.10
GRID = [0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40]
N_PER_DOMAIN = 120
SEED = 11
MIN_SUPPORT = 5
CO_CHANCE_CAP = 0.5
SEL_LO_FALLBACK = 0.0417                        # step-1 band lo (used only to report)
SEL_HI_FALLBACK = 0.7071

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "2026-10-19-rung3-positive-control-results.json")

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
    print(f"CORPUS {len(cook)} cooking / {len(astro)} astronomy; "
          f"0 shared tokenizer ids (gemma tokenizer, add_special_tokens=False)")
    return cook, astro


@torch.no_grad()
def encode(model, sae, tok, texts, batch=16):
    """Per-passage max SAE activation. Padded batches, masked to real tokens."""
    feats = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        enc = tok(chunk, return_tensors="pt", padding=True)
        out = model(**enc, output_hidden_states=True)
        resid = out.hidden_states[LAYER + 1].float()
        mask = enc["attention_mask"].bool()
        f = sae.encode(resid.reshape(-1, resid.shape[-1]))
        f = f.reshape(resid.shape[0], resid.shape[1], -1)
        f = f.masked_fill(~mask.unsqueeze(-1), float("-inf"))
        feats.append(f.amax(dim=1).cpu().numpy())
    return np.concatenate(feats, axis=0)


def derive_band(hist_rates, n_passages):
    """§2 rule, re-derived from the histogram (step 1)."""
    support = hist_rates * n_passages
    lo_candidates = hist_rates[support >= MIN_SUPPORT]
    lo = float(lo_candidates.min()) if lo_candidates.size else float(hist_rates.max())
    hi = min(float(np.sqrt(CO_CHANCE_CAP)), float(hist_rates.max()))
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
        "top_feature": int(sel[best_i]),
        "top_rate": float(obs[best_i]), "top_perm_mean": float(mu[best_i]),
        "z_obs": z_obs, "obs": obs, "perm_mean": mu, "sel": sel,
    }


def main():
    print("=== #144 rung-3 step 2: frozen positive control ===")
    model, tok = load_model()
    cook, astro = build_corpus(tok)
    n = min(len(cook), len(astro))

    from sae_lens import SAE
    t0 = time.time()
    sae = SAE.from_pretrained(release=SAE_RELEASE, sae_id=SAE_ID, device="cpu")
    print(f"SAE {SAE_RELEASE} / {SAE_ID} loaded wall={time.time() - t0:.1f}s "
          f"d_in={sae.cfg.d_in} d_sae={sae.cfg.d_sae} "
          f"hook={sae.cfg.metadata.hook_name}")

    # ---- clean encodings (also the step-1 band source) ----
    maxk = int(max(GRID) * n)
    cache = OUT.replace(".json", "-acts.npz")
    t0 = time.time()
    if os.path.exists(cache):
        z = np.load(cache)
        fc0, fa0, fc_plant, fa_plant = z["fc0"], z["fa0"], z["fcp"], z["fap"]
        print(f"loaded cached encodings from {cache}")
    else:
        fc0 = encode(model, sae, tok, cook)
        fa0 = encode(model, sae, tok, astro)
        print(f"clean encodings: {time.time() - t0:.1f}s peak_rss={rss_gb():.2f} GB")

        # ---- appended encodings for the max injected count ----
        rng0 = np.random.default_rng(SEED)
        perm0 = rng0.permutation(n)
        plant_idx_all = sorted(perm0[:maxk].tolist())
        t0 = time.time()
        fcp = encode(model, sae, tok, [cook[i] + f" {PLANT_TOKEN}" for i in plant_idx_all])
        fap = encode(model, sae, tok, [astro[i] + f" {PLANT_TOKEN}" for i in plant_idx_all])
        print(f"planted encodings ({maxk} passages): {time.time() - t0:.1f}s "
              f"peak_rss={rss_gb():.2f} GB")
        # scatter back to full-length arrays indexed by passage
        fc_plant = np.full_like(fc0, -np.inf)
        fa_plant = np.full_like(fa0, -np.inf)
        for j, i in enumerate(plant_idx_all):
            fc_plant[i] = fcp[j]
            fa_plant[i] = fap[j]
        np.savez_compressed(cache, fc0=fc0, fa0=fa0, fcp=fc_plant, fap=fa_plant)

    rc, ra = (fc0 > 0).mean(axis=0), (fa0 > 0).mean(axis=0)
    all_rates = np.concatenate([rc, ra])
    lo, hi = derive_band(all_rates[all_rates > 0], N_PER_DOMAIN)
    print(f"selectivity band re-derived: lo={lo:.4f} hi={hi:.4f}")

    # ---- grid ----
    rng = np.random.default_rng(SEED)
    perm = rng.permutation(n)

    def mix(rate):
        k = int(round(rate * n))
        if rate > 0:
            k = max(2, k)
        mask = np.zeros(n, bool)
        mask[np.array(sorted(perm[:k].tolist()), dtype=int)] = True
        fc = np.where(mask[:, None], fc_plant, fc0)
        fa = np.where(mask[:, None], fa_plant, fa0)
        return k, mask, fc, fa

    def margins(mask, fc, fa):
        inj, notinj = mask, ~mask
        mc = fc[inj].mean(0) - fc[notinj].mean(0)
        ma = fa[inj].mean(0) - fa[notinj].mean(0)
        return mc, ma, np.minimum(mc, ma)

    # The planted feature is a property of the token, not of the rate: identify
    # it once at the highest grid rate (most injections → highest-power margin),
    # then read its margin / band membership / z at every rate.
    _, mask_hi, fc_hi, fa_hi = mix(max(GRID))
    mc_hi, ma_hi, _ = margins(mask_hi, fc_hi, fa_hi)
    planted = int(np.argmax(np.minimum(mc_hi, ma_hi)))
    print(f"planted feature (max-margin at rate={max(GRID)}): {planted} "
          f"margin=({mc_hi[planted]:+.2f},{ma_hi[planted]:+.2f})")

    per_rate = {}
    for rate in GRID:
        k, mask, fc, fa = mix(rate)
        bc, ba = fc > 0, fa > 0
        entry = {"rate": rate, "n_injected": int(k)}
        if k == 0:
            entry["note"] = "clean arm; no injection, no constructibility"
            per_rate[str(rate)] = entry
            print(f"  rate={rate:<6} k=0    clean arm (no injection)")
            continue

        mc_all, ma_all, min_margin = margins(mask, fc, fa)
        mc, ma = float(mc_all[planted]), float(ma_all[planted])
        rate_c, rate_a = float(bc[:, planted].mean()), float(ba[:, planted].mean())
        in_band = bool(lo <= rate_c <= hi and lo <= rate_a <= hi)
        entry["planted_feature"] = planted
        entry["constructibility_margin"] = {"cooking": mc, "astronomy": ma,
                                            "both_positive": bool(mc > 0 and ma > 0)}
        entry["planted_firing_rate_injected"] = {"cooking": rate_c, "astronomy": rate_a}
        entry["planted_in_band_both_domains"] = in_band
        entry["planted_firing_rate_clean"] = {"cooking": float(rc[planted]),
                                              "astronomy": float(ra[planted])}
        entry["planted_rate_shift"] = {"cooking": rate_c - float(rc[planted]),
                                       "astronomy": rate_a - float(ra[planted])}

        # The detector's family at this rate: features whose injected firing rate
        # is inside [lo, hi] in both domains.
        sel = np.where((bc.mean(0) >= lo) & (bc.mean(0) <= hi) &
                       (ba.mean(0) >= lo) & (ba.mean(0) <= hi))[0]
        if sel.size < 2:
            entry["note"] = "no family at this rate"
            entry["planted_recovered"] = False
            per_rate[str(rate)] = entry
            print(f"  rate={rate:<6} k={k:<3} no family")
            continue

        r = evaluate(bc, ba, sel, n, np.random.default_rng(SEED))
        entry.update({
            "n_family": r["n_family"], "best_z": r["best_z"],
            "cutoff_z": r["cutoff_z"], "n_survivors": r["n_survivors"],
            "survivor_features": r["survivor_features"],
            "top_feature": r["top_feature"], "top_rate": r["top_rate"],
        })
        # (c) the planted feature's z versus the family-wise cutoff. Undefined if
        # the planted feature is not itself a family member (out of band).
        pos = np.where(r["sel"] == planted)[0]
        if pos.size:
            j = int(pos[0])
            entry["planted_z"] = float(r["z_obs"][j])
            entry["planted_rate"] = float(r["obs"][j])
            entry["planted_perm_mean"] = float(r["perm_mean"][j])
            entry["planted_recovered"] = bool(r["z_obs"][j] > r["cutoff_z"])
        else:
            entry["planted_z"] = None
            entry["planted_recovered"] = False
            entry["planted_note"] = "planted feature outside the selectivity band"
        # secondary: is the statistic's own top pick plant-driven?
        tz = r["top_feature"]
        entry["top_feature_constructibility_margin"] = {
            "cooking": float(mc_all[tz]), "astronomy": float(ma_all[tz]),
            "both_positive": bool(mc_all[tz] > 0 and ma_all[tz] > 0)}
        per_rate[str(rate)] = entry
        pz = entry["planted_z"]
        print(f"  rate={rate:<6} k={k:<3} |fam|={r['n_family']:<5} "
              f"best_z={r['best_z']:6.2f} cutoff={r['cutoff_z']:5.2f} "
              f"surv={r['n_survivors']:<3} margin=({mc:+.2f},{ma:+.2f}) "
              f"in_band={int(in_band)} pz={'None' if pz is None else f'{pz:.2f}'} "
              f"rec={entry['planted_recovered']}")

    # ---- verdict ----
    constructible = [r for r in per_rate.values()
                     if r.get("constructibility_margin", {}).get("both_positive")]
    recovered = [r for r in constructible if r.get("planted_recovered")]
    mid = [r for r in recovered if r["rate"] <= 0.10]
    if not constructible:
        verdict = "control-not-constructible"
    elif not recovered:
        verdict = "control-not-recovered"
    elif mid:
        verdict = "recovered"
    else:
        verdict = "recovered-only-above-mid-grid"
    print(f"\n=== summary ===\n  planted feature: {planted}")
    print(f"  constructible rates: {[r['rate'] for r in constructible]}")
    print(f"  planted-feature-recovered rates: {[r['rate'] for r in recovered]}")
    print(f"  verdict: {verdict}")

    out = {
        "run_id": "20261019-0101-05fv", "issue": 144, "step": "rung3-step2",
        "model": MIRROR, "model_official": MODEL_OFFICIAL,
        "model_revision": MIRROR_REVISION,
        "dtype": str(DTYPE), "device": "cpu",
        "sae": {"release": SAE_RELEASE, "sae_id": SAE_ID, "hook": HOOK,
                "d_in": int(sae.cfg.d_in), "d_sae": int(sae.cfg.d_sae)},
        "corpus": {"n_per_domain": n, "seed": SEED, "token_disjoint": True},
        "firing_rule": "gt0",
        "plant": {"token": PLANT_TOKEN, "rate": PLANT_RATE, "grid": GRID,
                  "construction": "append token to paired passage in both domains; "
                                  "per-passage max activation is monotone under appending, "
                                  "so clean + appended encodings are mixed per rate",
                  "n_injected_max": maxk,
                  "planted_feature": planted,
                  "planted_feature_selection": "argmax over features of "
                                               "min(margin_cooking, margin_astronomy) "
                                               "at the highest grid rate (highest power)"},
        "band": {"lo": lo, "hi": hi,
                 "note": "re-derived from the same corpus; step-1 reported "
                         "[0.0417, 0.7071]"},
        "statistic": "standardized per-feature matched-pairing co-activation z",
        "null_model": f"pairing permutation, N_PERM={N_PERM}",
        "correction": "family-wise max-statistic on the standardized statistic "
                      "(95th pct over permutations of max per-feature z)",
        "per_rate": per_rate,
        "verdict": verdict,
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
