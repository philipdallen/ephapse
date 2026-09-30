#!/usr/bin/env python3
"""G-M1, G-M2 — program label-state gates (issue #30).

Tier 0. Reads the committed issue-state cache only; never the network.

| ID   | Check |
|------|-------|
| G-M1 | Exactly one `status:` and exactly one `kind:` label per OPEN issue |
| G-M2 | Dependency coherence — an `status:available` issue has no OPEN blocker |

WHY TWO GATES AND NOT ONE. G-M1 alone would not have caught the failure that
motivated this work. Three label-state defects appeared in a single session:

  1. **Invalid mutation.** Filing #29-#34 set *both* `status:available` and
     `status:blocked-needs-input` on the same issue. G-M1 catches this.
  2. **Dependency violation.** #32 and #33 were marked `status:available` while
     their declared blocker #31 was OPEN. Their label *cardinality* was correct —
     one status each — so G-M1 is silent. Only a check that reads the dependency
     graph sees it. That is G-M2.
  3. **Omission.** The #31 dependency link was never created at all, so #32/#33
     had no `blocked_by` edge and nothing to violate. **No gate catches this**,
     because absence of an edge is indistinguishable from a task with no
     dependencies. It is a filing-protocol defect, addressed by the setter in
     `tooling/program/issue_state.py` and by the spec's task map being the
     authority for what edges should exist.

So a gate is *detection*, and detection is partial. The same session produced a
defect no gate can see, which is why this issue also lands a *preventer*.

THE CACHE. `tests/fixture_issue_state.json`, extended with two fields per issue:

    {"28": {"state": "CLOSED", "done": true,
            "labels": ["status:done", "kind:protocol"],
            "blocked_by": []}}

Entries whose key starts with `_` are metadata and ignored. The `state`/`done`
fields are G-E7's and must not change; `labels` and `blocked_by` are additive.

Both gates return SKIP — never pass — when the cache is absent or lacks issues,
following the G-E7 precedent exactly.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from run_all import Gate, register           # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
ISSUE_CACHE = REPO / "tests" / "fixture_issue_state.json"

STATUS_LABEL_RE = re.compile(r"^status:")
KIND_LABEL_RE = re.compile(r"^kind:")

# The registered vocabularies. A value outside these is its own defect class:
# a typo'd label is invisible to a cardinality check and silently divides the
# queue.
#
# Statuses stay here. Kinds are read from the single machine-readable source
# (DEC-035) because they are also read by tooling/program/issue_state.py, and a
# vocabulary living in two code paths drifts.
VALID_STATUS = (
    "status:available", "status:claimed", "status:done",
    "status:blocked-needs-input",
)
KIND_VOCABULARY_FILE = (
    Path(__file__).resolve().parent.parent / "program" / "kind_vocabulary.txt"
)


def load_kind_vocabulary(path: Path | None = None) -> tuple[str, ...]:
    """Read the kind values from the single machine-readable source (DEC-035).

    Raises rather than returning an empty tuple: a gate that silently validates
    against no vocabulary would pass every label, which is the vacuity failure
    DEC-019 and DEC-020 were both about.

    This is called lazily inside the gate, not at import — a module-level raise
    would crash `run_all.py` on import, and a gate must *fail*, not take the
    runner down.

    `path` defaults to `None` and the module global is read at call time. A
    default of `KIND_VOCABULARY_FILE` would bind at import and make the
    missing-file path un-monkeypatchable — a probe of that path returned a
    misleading PASS because the default still pointed at the real file. The
    G-E7 precedent reads its module global at call time for the same reason.
    """
    if path is None:
        path = KIND_VOCABULARY_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"kind vocabulary missing: {path} — G-M1 cannot validate labels "
            f"without it (see DEC-035)")
    values = tuple(
        line.strip() for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if not values:
        raise ValueError(f"kind vocabulary is empty: {path}")
    return values


def _load_cache(path: Path) -> tuple[dict | None, list[str]]:
    """Return (issues, errors). `issues` excludes metadata keys."""
    if not path.exists():
        return None, [f"issue-state cache absent ({path.name})"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return None, [f"issue-state cache unreadable ({e.msg})"]
    if not isinstance(raw, dict):
        return None, ["issue-state cache is not a JSON object"]
    issues = {k: v for k, v in raw.items()
              if not k.startswith("_") and isinstance(v, dict)}
    return issues, []


def _open_issues(issues: dict) -> dict:
    return {k: v for k, v in issues.items()
            if str(v.get("state", "")).upper() == "OPEN"}


def _labels(entry: dict) -> list[str]:
    labels = entry.get("labels")
    return list(labels) if isinstance(labels, list) else []


# ------------------------------------------------------------------- G-M1
def check_label_cardinality(path: Path) -> tuple[str, list[str]]:
    """G-M1: exactly one status: and one kind: per OPEN issue."""
    issues, errors = _load_cache(path)
    if issues is None:
        return "SKIP", errors

    open_issues = _open_issues(issues)
    if not open_issues:
        return "SKIP", ["no OPEN issues in the cache — nothing to check"]

    # Load the vocabulary lazily (DEC-035). A missing or empty source means the
    # check cannot run, which is SKIP-with-reason — never PASS, and never a
    # crash. A gate that validated against no vocabulary would accept every
    # label, which is the vacuity failure DEC-019/DEC-020 were both about.
    try:
        valid_kind = load_kind_vocabulary()
    except (FileNotFoundError, ValueError) as e:
        return "SKIP", [f"kind vocabulary unavailable — {e}"]

    findings: list[str] = []
    for num, entry in sorted(open_issues.items(), key=lambda kv: int(kv[0])
                             if kv[0].isdigit() else 0):
        labels = _labels(entry)
        if not labels:
            # A label-less entry may simply mean the cache predates labels.
            # Skipping the whole check would hide real violations, so it is
            # reported as a finding: an unlabeled cached issue cannot be
            # verified and must be refreshed.
            findings.append(f"G-M1 #{num}: cache entry carries no `labels` "
                            f"list — refresh the cache (tooling/program/"
                            f"issue_state.py)")
            continue
        statuses = [l for l in labels if STATUS_LABEL_RE.match(l)]
        kinds = [l for l in labels if KIND_LABEL_RE.match(l)]
        if len(statuses) != 1:
            findings.append(f"G-M1 #{num}: {len(statuses)} status label(s) "
                            f"({', '.join(statuses) or 'none'}) — exactly one "
                            f"required")
        if len(kinds) != 1:
            findings.append(f"G-M1 #{num}: {len(kinds)} kind label(s) "
                            f"({', '.join(kinds) or 'none'}) — exactly one "
                            f"required")
        # Vocabulary, not just cardinality. A typo'd label reads as one label
        # and silently divides the queue — the failure mode a count cannot see.
        for label in statuses:
            if label not in VALID_STATUS:
                findings.append(f"G-M1 #{num}: {label!r} is not a known status "
                                f"label — expected one of "
                                f"{', '.join(VALID_STATUS)}")
        for label in kinds:
            if label not in valid_kind:
                findings.append(f"G-M1 #{num}: {label!r} is not a known kind "
                                f"label — expected one of "
                                f"{', '.join(valid_kind)}")
    if not findings:
        return "PASS", []
    return "FAIL", findings


# ------------------------------------------------------------------- G-M2
def check_dependency_coherence(path: Path) -> tuple[str, list[str]]:
    """G-M2: an `available` issue must have no OPEN blocker.

    This is the check G-M1 cannot do. A forbidden-state combination, not a
    cardinality error: #32 with `status:available` and an OPEN `blocked_by`
    entry is invalid even though it carries exactly one status label.

    **Vacancy guard.** The first version of this gate reported PASS while
    checking nothing, because `blocked_by` was empty for every cached issue —
    `gh issue list` cannot read dependencies, so a refresh leaves the field
    empty and the gate finds no violations in a graph it never saw. A green
    result that cannot come out red is not a result (DEC-019, DEC-020). So when
    no cached issue carries any `blocked_by` entry, the gate returns SKIP with
    the reason rather than PASS: it cannot distinguish "no violations" from
    "no dependency data".
    """
    issues, errors = _load_cache(path)
    if issues is None:
        return "SKIP", errors
    if not issues:
        return "SKIP", ["issue-state cache is empty — nothing to check"]

    # Vacancy guard: without any recorded edges there is nothing to contradict.
    if not any((v.get("blocked_by") or []) for v in issues.values()):
        return "SKIP", [
            "no `blocked_by` edges recorded in the cache — cannot check "
            "dependency coherence. `gh issue list` cannot read dependencies; "
            "populate them with `tooling/program/issue_state.py block` or a "
            "GraphQL refresh."]

    findings: list[str] = []
    for num, entry in sorted(issues.items(), key=lambda kv: int(kv[0])
                             if kv[0].isdigit() else 0):
        labels = _labels(entry)
        blocked_by = entry.get("blocked_by") or []
        if not isinstance(blocked_by, list):
            findings.append(f"G-M2 #{num}: `blocked_by` is not a list")
            continue
        if not blocked_by:
            continue
        open_blockers = [
            b for b in blocked_by
            if str(issues.get(str(b), {}).get("state", "")).upper() != "CLOSED"
        ]
        if open_blockers and "status:available" in labels:
            findings.append(
                f"G-M2 #{num}: status:available but blocker(s) "
                f"{', '.join('#' + str(b) for b in open_blockers)} not CLOSED "
                f"— a blocked task must not be claimable")
    if not findings:
        return "PASS", []
    return "FAIL", findings


register(Gate(
    id="G-M1", name="label cardinality", tier=0,
    check=lambda p: [],                      # check_status form is authoritative
    check_status=check_label_cardinality,
    clean_fixture="program_clean.json",
    failing_fixture="program_r1_two_status.json",
    traces_to="PROGRAM_MANAGEMENT_SPEC.md section 7",
    description="Exactly one status: and exactly one kind: per OPEN issue.",
))

register(Gate(
    id="G-M2", name="dependency coherence", tier=0,
    check=lambda p: [],
    check_status=check_dependency_coherence,
    clean_fixture="program_clean.json",
    failing_fixture="program_r2_available_blocked.json",
    traces_to="PROGRAM_MANAGEMENT_SPEC.md section 4; MULTI_AGENT_WORKFLOW.md section 1a",
    description="An available issue has no open blocker.",
))


# ------------------------------------------------------------------- G-M3
def check_ledger_rule1_artifacts(path: Path) -> tuple[str, list[str]]:
    """G-M3: a ledger rule-1 outcome must rest on artifacts that exist.

    Rule 1 (`outcome` requires `results` or `findings`) was satisfiable by a
    string: the check only counted the lists, never touched the filesystem, so
    an outcome could rest on an absent artifact or cite a finding line outside
    `findings.jsonl` (issue #85). This gate asserts the mechanical half of the
    fix — existence of each `results` path, and range of each `findings` line.

    `path` is the fixture **directory** holding `ledger.jsonl` and the
    `findings.jsonl` the citations are resolved against; both resolve relative
    to that directory, so the gate never reads the live repo file whose record
    lines drift as evidence is appended. Semantic correctness — whether the
    artifact passed its downstream gate — is deliberately out of scope (the
    issue says so); existence and range are what a tier-0 gate can check.

    `program/` is not a package, so ledger.py is imported by path rather than by
    name. A gate must fail, not crash, so an import error is reported as a
    finding rather than allowed to propagate into run_all's BROKEN path.
    """
    ledger_jsonl = path / "ledger.jsonl"
    if not ledger_jsonl.exists():
        return "SKIP", [f"ledger fixture absent ({ledger_jsonl.name})"]

    program_dir = REPO / "program"
    if str(program_dir) not in sys.path:
        sys.path.insert(0, str(program_dir))
    try:
        import ledger as L
    except Exception as e:  # noqa: BLE001 - a gate fails, it does not crash
        return "FAIL", [f"cannot import program/ledger.py — {type(e).__name__}: {e}"]

    try:
        records = L.read_ledger(ledger_jsonl)
    except Exception as e:  # noqa: BLE001 - a gate fails, it does not crash
        return "FAIL", [f"ledger fixture unreadable — {type(e).__name__}: {e}"]

    findings: list[str] = []
    for rec in records:
        try:
            rec.validate(results_root=path, findings_path=path / "findings.jsonl")
        except L.LedgerError as e:
            findings.append(f"G-M3 {rec.id}: {e}")
        except Exception as e:  # noqa: BLE001 - a gate fails, it does not crash
            findings.append(f"G-M3 {rec.id}: validation raised "
                            f"{type(e).__name__}: {e}")
    if not findings:
        return "PASS", []
    return "FAIL", findings


register(Gate(
    id="G-M3", name="ledger rule-1 artifacts", tier=0,
    check=lambda p: [],
    check_status=check_ledger_rule1_artifacts,
    clean_fixture="program_ledger",
    failing_fixture="program_ledger_missing_artifact",
    traces_to="PROGRAM_MANAGEMENT_SPEC.md section 4; issue #85",
    description="A rule-1 outcome's `results` exist and its `findings` lines "
                "are real record lines.",
))


# ------------------------------------------------------------------- G-E9
# `verdict` (findings.jsonl) and `outcome` (the ledger) are orthogonal by
# design, and §3.2's load-bearing distinction is that `instrument-failed` and
# `phenomenon-present` both permit a `flagged` label while meaning opposite
# things about the world. Nothing joined them: the ledger record's `findings:
# [N]` link was unconstrained by its own `outcome`, so a record with
# `outcome: instrument-failed` and `findings: [62]` (a `flagged` line) validated
# cleanly (issue #87). This gate is that join.
#
# A `flagged` finding is a *claim about the world* — a co-activation that
# survived the controls. It may only rest on an apparatus that worked:
# `instrument-validated` or `phenomenon-present`. An instrument that failed
# cannot carry a flagged phenomenon, so `instrument-failed` paired with a
# `flagged` citation is rejected.
#
# Scope, stated because a gate is partial by construction: `defect-found` and
# `requirement-emerged` are claims *about the work*, not about the world, so a
# flagged citation there is rejected too — the gate only accepts the two outcomes
# that can carry a world-claim. A `null` finding line is not a phenomenon claim,
# so it is not flagged-reachable evidence either way and is never rejected.
def check_flagged_findings_reachability(path: Path) -> tuple[str, list[str]]:
    """G-E9: a `flagged` finding cannot rest on an `instrument-failed` outcome.

    `path` is the fixture **directory** holding `ledger.jsonl` and the
    `findings.jsonl` the citations are resolved against (the G-M3 form, so the
    check runs against a fixture tree rather than the live files, whose record
    lines drift as evidence is appended). The gate reads `outcome` from the
    ledger and `verdict` from the cited finding line — neither file carries the
    other's field, which is why this is a cross-file join and not a schema check.
    """
    ledger_jsonl = path / "ledger.jsonl"
    if not ledger_jsonl.exists():
        return "SKIP", [f"ledger fixture absent ({ledger_jsonl.name})"]
    findings_jsonl = path / "findings.jsonl"
    if not findings_jsonl.exists():
        return "SKIP", [f"findings fixture absent ({findings_jsonl.name})"]

    program_dir = REPO / "program"
    if str(program_dir) not in sys.path:
        sys.path.insert(0, str(program_dir))
    try:
        import ledger as L
    except Exception as e:  # noqa: BLE001 - a gate fails, it does not crash
        return "FAIL", [f"cannot import program/ledger.py — {type(e).__name__}: {e}"]

    try:
        records = L.read_ledger(ledger_jsonl)
    except Exception as e:  # noqa: BLE001 - a gate fails, it does not crash
        return "FAIL", [f"ledger fixture unreadable — {type(e).__name__}: {e}"]

    # Resolve each cited line to its `verdict`. Read the file as physical lines
    # so a citation's line number means the same thing the ledger's own rule-1
    # check means by it. A line that does not parse, or carries no `verdict`
    # string, is not a `flagged` finding and cannot trigger this gate; the
    # missing/out-of-range citation is already G-M3's finding, not a second one.
    verdicts: dict[int, object] = {}
    for i, line in enumerate(
            findings_jsonl.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            verdicts[i] = rec.get("verdict")

    # Outcome classes that permit a `flagged` finding — a claim about the world.
    # `instrument-validated` (the apparatus was shown to work) and
    # `phenomenon-present` (a measurement that found something) only.
    FLAGGED_REACHABLE = ("instrument-validated", "phenomenon-present")

    findings: list[str] = []
    for rec in records:
        if rec.outcome is None:
            continue
        for entry in rec.findings:
            if not isinstance(entry, int) or isinstance(entry, bool):
                continue
            if verdicts.get(entry) != "flagged":
                continue
            if rec.outcome == "instrument-failed":
                findings.append(
                    f"G-E9 {rec.id}: outcome `instrument-failed` cites flagged "
                    f"finding line {entry} — an instrument that failed cannot "
                    f"carry a flagged phenomenon (spec §3.2)")
            elif rec.outcome not in FLAGGED_REACHABLE:
                findings.append(
                    f"G-E9 {rec.id}: outcome `{rec.outcome}` cites flagged "
                    f"finding line {entry} — a flagged finding requires outcome "
                    f"in {FLAGGED_REACHABLE} (spec §3.2)")
    if not findings:
        return "PASS", []
    return "FAIL", findings


register(Gate(
    id="G-E9", name="flagged-finding reachability", tier=0,
    check=lambda p: [],
    check_status=check_flagged_findings_reachability,
    clean_fixture="program_ledger_flagged_reachable",
    failing_fixture="program_ledger_flagged_on_instrument_failed",
    traces_to="PROGRAM_MANAGEMENT_SPEC.md section 3.2; issue #87",
    description="A `flagged` finding cannot rest on an `instrument-failed` "
                "outcome — the join between `verdict` and `outcome`.",
))
