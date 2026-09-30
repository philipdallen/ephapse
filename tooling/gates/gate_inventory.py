#!/usr/bin/env python3
"""Single source for the gate-count figures (issues #38, #88).

Three figures circulated in prose (37, 38, "7 wired") and disagreed with the
registry. The spec's own § 3 inventory table is the authority for the
**specified** count — it enumerates the gate ids — so that count is derived
from it here rather than hand-copied. The **wired** count is the number of ids
`run_all.py` actually registers; it is read from the live registry for the same
reason. Prose that quotes either figure should cite this module's output, not a
typed number.

Usage:
    python3 tooling/gates/gate_inventory.py           # human summary
    python3 tooling/gates/gate_inventory.py --json     # machine-readable
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SPEC = REPO / "docs" / "reference" / "TEST_VALIDATION_SPEC.md"

# A row of the § 3 inventory: | **G-P1** | description | provenance | tier |
_ROW = re.compile(r"^\|\s*\*\*(G-[A-Z]\d+)\*\*\s*\|(.*)\|\s*([0-9/]+)\s*\|\s*$")


def counts(spec_path: Path = SPEC) -> dict:
    """Derive the totals from the spec inventory table.

    `tier` is the spec's own column: "0" is tier-0 only, "1" is tier-1 only,
    and "0/1" marks a gate that is tier-0 capable but conditionally needs more
    (G-P2, the tokenizer-level check). `tier0` counts every id that can run at
    tier 0, which is why G-P2 is included.
    """
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in spec_path.read_text().splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        gid, tier = m.group(1), m.group(3)
        if gid in seen:  # duplicates would be a spec defect, not a count
            continue
        seen.add(gid)
        rows.append((gid, tier))

    tiers = {"0": 0, "1": 0, "0/1": 0}
    for _, tier in rows:
        tiers[tier] = tiers.get(tier, 0) + 1

    return {
        "total": len(rows),
        "tier0": tiers["0"] + tiers["0/1"],
        "tier1": tiers["1"],
        "tier0_only": tiers["0"],
        "conditional": tiers["0/1"],
        "ids": [gid for gid, _ in rows],
    }


def registered_ids() -> list[str]:
    """Return the ids `run_all.py` actually wires, from the live registry.

    `run_all.py` discovers its gates by importing the `validate_*.py` /
    `check_*.py` modules beside it; importing it here runs that discovery, so the
    count cannot drift from the runner the way a hand-typed figure did.
    """
    import run_all

    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    # `_load_gate_modules` appends to a module-level REGISTRY without clearing it,
    # so calling it twice would double the list. Rebuild from empty and restore,
    # which keeps this function idempotent for any caller.
    saved = list(run_all.REGISTRY)
    run_all.REGISTRY.clear()
    try:
        run_all._load_gate_modules()
        return sorted({g.id for g in run_all.REGISTRY})
    finally:
        run_all.REGISTRY[:] = saved


def main() -> int:
    c = counts()
    c["wired"] = registered_ids()
    c["wired_total"] = len(c["wired"])
    if "--json" in sys.argv:
        print(json.dumps(c, indent=2))
        return 0
    print(f"specified gate ids: {c['total']}")
    print(f"tier-0 capable:     {c['tier0']}  (of which {c['conditional']} conditional)")
    print(f"tier-1 only:        {c['tier1']}")
    print(f"wired (registered): {c['wired_total']}  ({', '.join(c['wired'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
