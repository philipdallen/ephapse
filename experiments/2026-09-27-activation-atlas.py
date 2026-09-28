"""Ep#82 — Render a model's activation structure as a visual artifact (atlas).

Produces a visual artifact of what a model's units *do*: which features respond
to which inputs, and which features move together. This is the producer half of
the ephapse -> rorschach handoff. rorschach consumes the PNG through
``ViewerField.from_images`` as an external second reading; no import crosses the
boundary (see docs/AGENT_HANDOFF.md for the coupling convention).

**Model:** pythia-70m-deduped (DEC-014), fp32, cpu.
**Inputs:** 16 fixed domain-varied prompts held in ``PROMPTS`` (probe set, not a
benchmark); activations pooled mean-over-tokens at ``blocks.3.hook_resid_post``.
**Question:** does rendering the residual-stream activation matrix to an image
recover a known injected structure (the render is not an instrument artefact)?
**Null:** the render is a fixed normalisation of the matrix; the null is that an
injected high-amplitude block is *not* the brightest region after normalisation.
**Correction:** none — this is a single instrument control, not a multiplicity of
tests. The atlas itself computes no statistic (rorschach D-008: no score).
**Issue:** #82 (visual artifact for the rorschach handoff).

**What this is.** A *feature response atlas*, not a picture of the bias vector.
A bias grid renders storage order, which looks like structure and means nothing.
Here each row is a real unit and each column a real input, so a cell can be
labelled with a concept later. Layout is a stated rule, never an aesthetic
choice -- otherwise the image shows the projection, not the model.

**What it is not.** An image is not a finding. This is ephapse's whole thesis: a
visual pattern is exactly the artifact that survives every check while meaning
nothing. So the render ships a positive control (`--selftest`): inject a known
block into the activations and confirm the atlas recovers it. If the control
fails, the render is `instrument-failed` and says so; it does not fall back to
"look, structure".

**External second reading (run 20260928-0241-pg59).** rorschach's consumer
(`examples/neural_field.py`, `ViewerField.from_images`, no import) reads the
render as an 8x8 field with spread 0.0017, below its 0.01 vacuity threshold, and
prints its own `WARNING: ... nearly flat; the constraint is close to vacuous`.
That is rorschach's instrument working: a normalised matrix rendered as a
picture can look structured while carrying almost no contrast between cells, so
its damping mask is near-uniform. Read the atlas as a *record* of which units
responded (the positive control holds); do not read its visual texture as
signal. The handoff is accepted on the coupling criterion, not on field spread.

Run: python3 experiments/2026-09-27-activation-atlas.py
"""

# GATE-DECL
# {
#   "statistic": {"name": "block_recovery", "kind": "rate",
#                  "rate": 1.0, "threshold": 1.0,
#                  "note": "binary recovery of an injected block; NOT the NPMI family, so G-C1 flags it for review by design — the render is a record, not a co-activation statistic"},
#   "control": {"computes_planted_presence": true,
#                "records_both_groups": true,
#                "constructible": "a high-amplitude block is stamped into a copy of the activations; recovery is read in feature space, so it cannot pass by pixel artefact"},
#   "readings": [{"name": "atlas_render", "gated_by": "block_recovery"},
#                 {"name": "similarity_render", "gated_by": "block_recovery"}],
#   "comparability": {"model": "pythia-70m-deduped",
#                      "hook": "blocks.3.hook_resid_post",
#                      "n": 16, "pooling": "mean over tokens", "seed": 0,
#                      "threshold": 1.0, "correction": "none"}
# }
# END-GATE-DECL
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

MODEL = "pythia-70m-deduped"
LAYER = 3
HOOK = f"blocks.{LAYER}.hook_resid_post"
OUT_DIR = Path(__file__).resolve().parent / "atlas"

# A small, fixed, domain-varied prompt set. Not a benchmark -- a probe set. Kept
# short so the run is cheap and re-runnable; the atlas is a record of one set of
# inputs, and provenance records exactly which.
PROMPTS = [
    "The Eiffel Tower is located in the city of Paris",
    "Photosynthesis converts light into chemical energy",
    "The prime minister announced a new policy on",
    "Integers form a ring under addition and",
    "Mitochondria are the powerhouse of the",
    "The stock market fell sharply after the",
    "Water boils at one hundred degrees",
    "Recursion is when a function calls",
    "The violinist tuned the instrument before the",
    "A theorem is a statement that has been",
    "The river eroded the bank over many",
    "Neurons fire when their input exceeds a",
    "The chef reduced the sauce until it",
    "Gravity bends light around a massive",
    "The novel opens with a description of",
    "A compiler translates source into machine",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- the render (deterministic, no model) -----------------------------------


def order_features(activations: np.ndarray) -> np.ndarray:
    """Row order for the atlas: descending mean absolute activation.

    A stated rule, not an aesthetic choice. It puts the units that move most at
    the top, so the eye reads a gradient of activity rather than storage order.
    """
    return np.argsort(-np.abs(activations).mean(axis=0))


def render_atlas(activations: np.ndarray, path: Path) -> np.ndarray:
    """Render an (n_prompts, d_model) activation matrix to a normalised PNG.

    The output is transposed to (d_model, n_prompts): each **row is a unit**,
    each **column is a prompt**. Rows are ordered by descending mean
    |activation| (:func:`order_features`), so the units that move most are at
    the top and the eye reads a gradient of activity rather than storage order.
    Features on rows also matches the similarity map, so the two panels share an
    axis. Normalised per-matrix to [0, 1] so the image is legible; raw values are
    kept in the provenance sidecar.
    """
    from PIL import Image

    ordered = activations[:, order_features(activations)].T  # (d_model, prompts)
    lo, hi = float(ordered.min()), float(ordered.max())
    span = hi - lo
    norm = (ordered - lo) / span if span > 1e-12 else np.zeros_like(ordered)
    img = Image.fromarray((norm * 255.0).astype(np.uint8), mode="L")
    img.save(path)
    return norm


def render_similarity(activations: np.ndarray, path: Path) -> np.ndarray:
    """Co-activation map: d_model x d_model cosine similarity, ordered.

    Features that fire together sit together, so adjacency carries information.
    This is the panel that can be segmented into candidate concept regions later.
    """
    from PIL import Image

    order = order_features(activations)
    a = activations[:, order]
    norms = np.linalg.norm(a, axis=0, keepdims=True)
    norms[norms < 1e-12] = 1.0
    unit = a / norms
    sim = unit.T @ unit  # (d_model, d_model), in [-1, 1]
    norm = (sim + 1.0) / 2.0
    Image.fromarray((norm * 255.0).astype(np.uint8), mode="L").save(path)
    return norm


# --- the positive control (RUNS-MUST-DETECT) --------------------------------


def _inject_block(activations: np.ndarray, rows: int = 6, cols: int = 5) -> tuple[np.ndarray, tuple]:
    """Stamp a known high-amplitude block into a copy of the activations."""
    a = activations.copy()
    r0 = a.shape[0] // 3
    c0 = a.shape[1] // 4
    a[r0:r0 + rows, c0:c0 + cols] = float(np.abs(a).max()) * 4.0
    return a, (r0, r0 + rows, c0, c0 + cols)


def selftest() -> int:
    """Confirm the renderer recovers a known injected signal.

    This validates the *instrument* (the render path), not the model. It is the
    same distinction ephapse draws everywhere: instrument-failed is not a finding
    about the phenomenon.
    """
    rng = np.random.default_rng(0)
    fake = rng.normal(0.0, 1.0, size=(len(PROMPTS), 64))
    injected, (r0, r1, c0, c1) = _inject_block(fake)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    before = OUT_DIR / "_selftest_before.png"
    after = OUT_DIR / "_selftest_after.png"
    n_before = render_atlas(fake, before)
    n_after = render_atlas(injected, after)

    # The injected block must be the brightest region after normalisation. Check
    # in *feature* space, not pixel space, so the test is about the pipeline's
    # ordering+scaling, not about how PIL happens to encode it.
    #
    # The render is transposed to (features, prompts), so the injected feature
    # columns c0:c1 land on output *rows*, and the injected prompt rows r0:r1
    # land on output *columns*.
    ordered_cols = order_features(injected)
    out_rows = [int(np.where(ordered_cols == c)[0][0]) for c in range(c0, c1)]
    block = n_after[out_rows, r0:r1]
    rest = np.delete(n_after, out_rows, axis=0)[:, r0:r1]
    detected = float(block.min()) > float(rest.max())

    print("selftest (instrument positive control)")
    print("-" * 38)
    print(f"  injected block      : rows {r0}:{r1}, features {c0}:{c1}")
    print(f"  block min (norm)    : {float(block.min()):.3f}")
    print(f"  background max      : {float(rest.max()):.3f}")
    print(f"  render differs      : {not np.array_equal(n_before, n_after)}")
    print(f"  verdict             : {'PASS' if detected else 'FAIL'}")

    before.unlink(missing_ok=True)
    after.unlink(missing_ok=True)
    return 0 if detected else 1


# --- the real run -----------------------------------------------------------


def collect_activations(prompts: list[str]) -> tuple[np.ndarray, dict]:
    """Mean-over-tokens residual activations: (n_prompts, d_model)."""
    import torch
    from transformer_lens import HookedTransformer

    model = HookedTransformer.from_pretrained(MODEL, device="cpu")
    with torch.no_grad():
        _, cache = model.run_with_cache(
            prompts, names_filter=lambda n: n == HOOK, return_type=None
        )
    acts = cache[HOOK]  # (batch, seq, d_model)
    pooled = acts.mean(dim=1).float().numpy()
    meta = {
        "model": MODEL,
        "hook": HOOK,
        "layer": LAYER,
        "d_model": int(pooled.shape[1]),
        "n_prompts": int(pooled.shape[0]),
        "pooling": "mean over tokens",
        "dtype": "float32",
    }
    return pooled, meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true",
                        help="run only the instrument positive control")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Always run the control first. A render whose control fails is not a result.
    if selftest() != 0:
        print("\ninstrument-failed: the render did not recover the injected signal.")
        print("No atlas written. This is an instrument failure, not a finding.")
        return 1

    try:
        activations, meta = collect_activations(PROMPTS)
    except Exception as exc:  # noqa: BLE001 - report, do not crash
        print(f"\ninstrument-failed: could not collect activations: {exc}")
        print("This is an instrument failure, not a finding about any model.")
        return 1

    atlas_path = OUT_DIR / "atlas.png"
    sim_path = OUT_DIR / "atlas_similarity.png"
    render_atlas(activations, atlas_path)
    render_similarity(activations, sim_path)

    provenance = {
        **meta,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "layout_rule": "rows are units ordered by descending mean |activation|; columns are prompts",
        "prompts": PROMPTS,
        "artifacts": {
            "atlas": {"path": atlas_path.name, "sha256": _sha256(atlas_path)},
            "similarity": {"path": sim_path.name, "sha256": _sha256(sim_path)},
        },
        "positive_control": "PASS (injected block recovered)",
        "not_a_score": (
            "Higher variation or contrast is not better. This is a record of what "
            "units responded to, not a judgement (D-008)."
        ),
    }
    (OUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2))

    print(f"\natlas        : {atlas_path}")
    print(f"similarity   : {sim_path}")
    print(f"provenance   : {OUT_DIR / 'provenance.json'}")
    print(f"  shape      : {activations.shape} (prompts x features)")
    print(f"  layout     : rows by descending mean |activation|")
    print("\nHand to rorschach:")
    print(f"  python examples/neural_field.py {atlas_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
