"""Composition-emergence Phase 1 probe: do SAE features emerge under composition?

**Model:** pythia-70m-deduped, fp32, CPU, SAE `pythia-70m-deduped-res-sm`,
  hook `blocks.3.hook_resid_post` (d_in=512, d_sae=32768).
**Inputs:** `experiments/composition_phase1_word_lists.json` (frozen Appendix A/B
  of the pre-registration, transcribed in #160): 18 idiom, 18 common, 18 novel,
  18 mismatched adjective+noun pairs, 10 synonym pairs, 10 verb+object pairs,
  each wrapped in its 3 fixed carriers.
**Question:** for composite c with constituents a, b, is there an SAE feature
  firing on c that fires on neither a nor b (emergence)?
**Null:** class-label permutation, N_PERM=400 (family-wise max-statistic over the
  three discovery classes); mismatched class is the null base rate.
**Correction:** family-wise max-statistic, 95th percentile of 400 permutation
  maxima; BH-FDR not used (DEC-016).
**Issue:** #161 (step 3/3 of the #158 decomposition; DEC-043).

Pre-registration: docs/reference/COMPOSITION_PREREGISTRATION.md (PR #157 branch).
Statistics frozen in §4; gates G1-G4 in §8; falsifiers F1-F4 in §7. No axis,
class, or threshold outside the pre-registration; deviations are reported.
"""
from __future__ import annotations

import json
import os

import numpy as np
import torch

MODEL = "pythia-70m-deduped"
MODEL_REVISION = "e93a9faa9c77e5d09219f6c868bfc7a1bd65593c"
SAE_RELEASE = "pythia-70m-deduped-res-sm"
HOOK = "blocks.3.hook_resid_post"

BATCH = 32
N_PERM = 400
SEED = 11

HERE = os.path.dirname(os.path.abspath(__file__))
LISTS = os.path.join(HERE, "composition_phase1_word_lists.json")
OUT = os.path.join(HERE, "2026-10-20-composition-phase1-probe-results.json")


def span_token_ids(tok, text: str, sub: str) -> list[int]:
    """Vocabulary ids of tokens whose character offsets overlap `sub` (#160)."""
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    off = enc["offset_mapping"]
    s = text.index(sub)
    e = s + len(sub)
    return [tid for tid, (a, b) in zip(enc["input_ids"], off) if a < e and b > s]


def span_positions(tok, text: str, sub: str) -> list[int]:
    """Positions in the token sequence of tokens overlapping `sub`."""
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    off = enc["offset_mapping"]
    s = text.index(sub)
    e = s + len(sub)
    return [i for i, (a, b) in enumerate(off) if a < e and b > s]


def tokenization_precondition(model, data) -> dict:
    """§3: composite target span tokenizes as concatenation of constituents."""
    tok = model.tokenizer
    res: dict[str, bool] = {}
    fails: list[tuple[str, str, str]] = []
    for arm, items in data["adj_noun"].items():
        for comp in items:
            ok_all = True
            for carrier in data["carriers"]["adj_noun"]:
                pre, suf = carrier.split("TARGET")
                a, b = comp.split(" ", 1)
                full = span_token_ids(tok, f"{pre}{comp}{suf}", comp)
                left = span_token_ids(tok, f"{pre}{a}{suf}", a)
                right = span_token_ids(tok, f"{pre}{b}{suf}", b)
                if full != left + right:
                    ok_all = False
                    fails.append((arm, comp, carrier))
            res[f"{arm}|{comp}"] = ok_all
    for comp in data["verb_object"]["verb_object"]:
        ok_all = True
        for carrier in data["carriers"]["verb_object"]:
            pre, suf = carrier.split("TARGET")
            a, b = comp.split(" ", 1)
            full = span_token_ids(tok, f"{pre}{comp}{suf}", comp)
            left = span_token_ids(tok, f"{pre}{a}{suf}", a)
            right = span_token_ids(tok, f"{pre}{b}{suf}", b)
            if full != left + right:
                ok_all = False
                fails.append(("verb_object", comp, carrier))
        res[f"verb_object|{comp}"] = ok_all
    return {"pair_status": res, "failures": fails,
            "n_pairs": len(res), "n_pass": sum(res.values())}


def encode_spans(model, sae, jobs: list[tuple[str, str]]):
    """jobs = [(text, target_substr)]. Returns max-over-span SAE activations.

    Batched by token length (padding is right-appended, so span positions stay
    valid). Returns a list aligned with `jobs`.
    """
    texts = [t for t, _ in jobs]
    order = sorted(range(len(texts)), key=lambda i: len(model.to_tokens(texts[i])[0]))
    out: list[np.ndarray | None] = [None] * len(jobs)
    with torch.no_grad():
        for i in range(0, len(order), BATCH):
            idxs = order[i:i + BATCH]
            batch = [texts[j] for j in idxs]
            toks = model.to_tokens(batch)
            _, cache = model.run_with_cache(
                toks, names_filter=lambda n: n == HOOK)
            acts = cache[HOOK]
            enc = sae.encode(acts.reshape(-1, acts.shape[-1])).reshape(
                acts.shape[0], acts.shape[1], -1).cpu().numpy()
            for row, j in enumerate(idxs):
                n_text = len(model.tokenizer(texts[j], add_special_tokens=False)["input_ids"])
                shift = toks.shape[1] - n_text
                pos = [p + shift for p in span_positions(
                    model.tokenizer, texts[j], jobs[j][1])]
                out[j] = enc[row, pos, :].max(axis=0)
            del cache, acts, enc
    return out


def profile_majority(mats: list[np.ndarray]) -> np.ndarray:
    """§2: feature fires iff max over span > 0 in >= 2 of 3 carriers."""
    fires = np.stack([m > 0.0 for m in mats], axis=0)
    return fires.sum(axis=0) >= 2


def jaccard_distance(a: np.ndarray, b: np.ndarray) -> float:
    inter = int((a & b).sum())
    union = int((a | b).sum())
    return 1.0 - (inter / union) if union else 0.0


def main() -> int:
    from sae_lens import SAE
    from transformer_lens import HookedTransformer

    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)

    print("=== #161 composition-emergence Phase 1 probe ===")
    with open(LISTS) as f:
        data = json.load(f)

    print("loading model + SAE ...")
    model = HookedTransformer.from_pretrained(
        MODEL, revision=MODEL_REVISION, dtype=torch.float32, device="cpu")
    sae = SAE.from_pretrained(release=SAE_RELEASE, sae_id=HOOK)
    sae = sae.to("cpu")
    print(f"model+SAE loaded; hook={HOOK}")

    # --- G4 precondition -------------------------------------------------
    print("\n--- G4 tokenization precondition (§3) ---")
    pre = tokenization_precondition(model, data)
    print(f"checked={pre['n_pairs']} pass={pre['n_pass']} "
          f"fail={len(pre['failures'])}")
    for f in pre["failures"]:
        print(f"  FAIL {f}")

    # --- build conditions ------------------------------------------------
    # Each class: pairs -> for each pair, conditions (a, b, c) x 3 carriers.
    adj_carriers = data["carriers"]["adj_noun"]
    verb_carriers = data["carriers"]["verb_object"]

    classes: dict[str, list[tuple[str, str, str]]] = {}
    for arm, items in data["adj_noun"].items():
        cls = "idiom" if arm == "idioms" else arm
        classes[cls] = []
        for comp in items:
            a, b = comp.split(" ", 1)
            classes[cls].append((a, b, comp))
    classes["verb_object"] = []
    for comp in data["verb_object"]["verb_object"]:
        a, b = comp.split(" ", 1)
        classes["verb_object"].append((a, b, comp))

    # Collect all (text, target) jobs, remembering per-condition carrier lists.
    def condition_jobs(pairs, carriers):
        """Return (jobs, mapping) where mapping[pair_i][cond] = list of job idx."""
        jobs, mapping = [], []
        for (a, b, c) in pairs:
            entry = {"a": [], "b": [], "c": []}
            for carrier in carriers:
                pre_t, suf = carrier.split("TARGET")
                for cond, tgt in (("a", a), ("b", b), ("c", c)):
                    jobs.append((f"{pre_t}{tgt}{suf}", tgt))
                    entry[cond].append(len(jobs) - 1)
            mapping.append(entry)
        return jobs, mapping

    all_jobs: list[tuple[str, str]] = []
    class_meta: dict[str, dict] = {}
    for name, pairs in classes.items():
        carriers = verb_carriers if name == "verb_object" else adj_carriers
        jobs, mapping = condition_jobs(pairs, carriers)
        base = len(all_jobs)
        all_jobs.extend(jobs)
        # shift job indices into the global list
        for entry in mapping:
            for k in entry:
                entry[k] = [v + base for v in entry[k]]
        class_meta[name] = {"pairs": pairs, "mapping": mapping}

    # Synonym arm: 2 single-word conditions per pair, no composite.
    syn_jobs, syn_map = [], []
    for (w1, w2) in data["synonym_pairs"]:
        entry = {"a": [], "b": []}
        for carrier in adj_carriers:
            pre_t, suf = carrier.split("TARGET")
            for cond, tgt in (("a", w1), ("b", w2)):
                syn_jobs.append((f"{pre_t}{tgt}{suf}", tgt))
                entry[cond].append(len(syn_jobs) - 1)
        syn_map.append(entry)

    print(f"\nencoding {len(all_jobs) + len(syn_jobs)} forward passes ...")
    acts = encode_spans(model, sae, all_jobs)
    syn_acts = encode_spans(model, sae, syn_jobs)

    # --- emergence -------------------------------------------------------
    results: dict[str, dict] = {}
    e_by_class: dict[str, list[float]] = {}
    ep_by_class: dict[str, list[float]] = {}
    dropped: list[str] = []

    for name, meta in class_meta.items():
        es, eps, comps = [], [], []
        for i, (a, b, c) in enumerate(meta["pairs"]):
            entry = meta["mapping"][i]
            Fa = profile_majority([acts[j] for j in entry["a"]])
            Fb = profile_majority([acts[j] for j in entry["b"]])
            Fc = profile_majority([acts[j] for j in entry["c"]])
            n_c = int(Fc.sum())
            if n_c == 0:
                dropped.append(f"{name}|{c}")
                continue
            emergent = Fc & (~Fa) & (~Fb)
            e_c = int(emergent.sum()) / n_c

            # secondary: co-firing pairs within each profile
            def pairs_of(F):
                idx = np.where(F)[0]
                if idx.size < 2:
                    return set()
                return {(int(x), int(y)) for i, x in enumerate(idx)
                        for y in idx[i + 1:]}
            Pc, Pa, Pb = pairs_of(Fc), pairs_of(Fa), pairs_of(Fb)
            ep_c = (len(Pc - (Pa | Pb)) / len(Pc)) if Pc else 0.0

            es.append(e_c)
            eps.append(ep_c)
            comps.append(c)
        e_by_class[name] = es
        ep_by_class[name] = eps
        results[name] = {
            "n_pairs": len(meta["pairs"]), "n_read": len(es),
            "mean_e": float(np.mean(es)) if es else None,
            "mean_ep": float(np.mean(eps)) if eps else None,
        }

    # --- synonym noise floor --------------------------------------------
    syn_d = []
    for i, (w1, w2) in enumerate(data["synonym_pairs"]):
        entry = syn_map[i]
        Fa = profile_majority([syn_acts[j] for j in entry["a"]])
        Fb = profile_majority([syn_acts[j] for j in entry["b"]])
        syn_d.append(jaccard_distance(Fa, Fb))
    syn_floor = float(np.percentile(syn_d, 95)) if syn_d else None

    # --- idiom positive-control bar (direct) -----------------------------
    mism = e_by_class.get("mismatched", [])
    idiom_bar = float(np.percentile(mism, 95)) if mism else None

    # --- discovery permutation null --------------------------------------
    disc_names = ["common", "novel", "verb_object"]
    pooled_vals, pooled_lab = [], []
    for name in disc_names + ["mismatched"]:
        for v in e_by_class.get(name, []):
            pooled_vals.append(v)
            pooled_lab.append(name)
    pooled_vals = np.array(pooled_vals)
    pooled_lab = np.array(pooled_lab)
    observed = {n: float(np.mean(e_by_class[n])) if e_by_class.get(n) else None
                for n in disc_names}
    maxima = np.empty(N_PERM)
    for p in range(N_PERM):
        perm = rng.permutation(pooled_lab)
        means = {n: pooled_vals[perm == n].mean() if (perm == n).any() else -np.inf
                 for n in disc_names}
        maxima[p] = max(means.values())
    cutoff = float(np.percentile(maxima, 95))

    # --- gates + falsifiers ----------------------------------------------
    idiom_mean = results["idiom"]["mean_e"]
    g1 = bool(idiom_mean is not None and idiom_bar is not None
              and idiom_mean > idiom_bar)
    clears = {}
    for n in disc_names:
        if observed[n] is None or syn_floor is None:
            clears[n] = False
            continue
        clears[n] = bool(observed[n] > cutoff and observed[n] > syn_floor)
    g2 = bool(clears["common"] or clears["novel"])
    # G3: not familiarity alone — only common clears, novel at base rate
    base = float(np.mean(mism)) if mism else None
    novel_at_base = bool(observed["novel"] is not None and base is not None
                         and observed["novel"] <= base)
    f3 = bool(g1 and clears["common"] and not clears["novel"] and novel_at_base)
    g3 = not f3
    g4 = bool(len(pre["failures"]) == 0)

    fired = []
    if not g1:
        fired.append("F1")
    if g1 and not g2:
        fired.append("F2")
    if f3:
        fired.append("F3")
    if syn_floor is not None and all(
            results[n]["mean_e"] is not None and results[n]["mean_e"] < syn_floor
            for n in disc_names):
        fired.append("F4")

    # --- report -----------------------------------------------------------
    print("\n=== class emergence (primary e, secondary ep) ===")
    print(f"{'class':<14}{'n':>4}{'mean_e':>10}{'mean_ep':>10}")
    for name in ["idiom", "common", "novel", "verb_object", "mismatched"]:
        r = results[name]
        me = "n/a" if r["mean_e"] is None else f"{r['mean_e']:.4f}"
        mp = "n/a" if r["mean_ep"] is None else f"{r['mean_ep']:.4f}"
        print(f"{name:<14}{r['n_read']:>4}{me:>10}{mp:>10}")

    print(f"\ndiscovery cutoff (95th pct of 400 family maxima) = {cutoff:.4f}")
    print(f"idiom positive-control bar (95th pct mismatched e) = "
          f"{idiom_bar if idiom_bar is None else round(idiom_bar, 4)}")
    print(f"synonym noise floor (95th pct of {len(syn_d)} Jaccard distances) = "
          f"{syn_floor if syn_floor is None else round(syn_floor, 4)}")
    print(f"mismatched base rate (mean e) = "
          f"{base if base is None else round(base, 4)}")
    if dropped:
        print(f"dropped pairs (|F(c)|=0): {len(dropped)}")

    print("\n=== gate verdicts (§8) ===")
    print(f"G1 instrument validated (idiom bar)      : {'PASS' if g1 else 'FAIL'}")
    print(f"G2 phenomenon beyond idioms              : {'PASS' if g2 else 'FAIL'}"
          f"  clears={clears}")
    print(f"G3 not familiarity alone                 : {'PASS' if g3 else 'FAIL'}")
    print(f"G4 tokenization precondition holds       : {'PASS' if g4 else 'FAIL'}"
          f"  ({pre['n_pass']}/{pre['n_pairs']})")
    print(f"\nfalsifiers fired: {fired if fired else 'none'}")

    out = {
        "issue": 161, "run_id": "20261020-0401-hq7k",
        "model": MODEL, "revision": MODEL_REVISION, "dtype": "float32",
        "device": "cpu", "sae": SAE_RELEASE, "hook": HOOK,
        "seed": SEED, "n_perm": N_PERM,
        "results": results,
        "e_by_class": {k: v for k, v in e_by_class.items()},
        "ep_by_class": {k: v for k, v in ep_by_class.items()},
        "discovery_cutoff": cutoff,
        "idiom_bar": idiom_bar,
        "synonym_floor": syn_floor,
        "synonym_jaccard": syn_d,
        "mismatched_base_rate": base,
        "gates": {"G1": g1, "G2": g2, "G3": g3, "G4": g4},
        "clears": clears, "falsifiers_fired": fired,
        "dropped_pairs": dropped,
        "tokenization": {"n_pairs": pre["n_pairs"], "n_pass": pre["n_pass"],
                         "failures": pre["failures"]},
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
