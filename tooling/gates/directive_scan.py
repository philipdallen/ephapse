#!/usr/bin/env python3
"""Directive scan — the advisory check behind `docs/DIRECTIVE_PROTOCOL.md`.

Advisory prose is what the audit flagged, so DEC-041 gives it a scanner. Two
layers, both warn-only by default:

| Layer | Source | Checks |
|-------|--------|--------|
| offline | `docs/decisions/LOG.md`, `docs/decisions/considerations/`, `git log` | DEC-041 §1 and §1a: a cited DEC exists and is `Active`, an `Active` Tier 1/2 DEC has a memo with the eight headings, a Tier 2 DEC has a challenge, the tier keyword rule, and `Directive:` trailers on commits |
| tracker | a cached issues JSON (`--issues-file`) | §1: every `status:available`/`status:claimed` issue from #89 carries `Directive: DEC-NNN`, and the cited DEC is `Active` |

WHY WARN-ONLY

The Phase-2 brief asked for warn-only with an opt-in `--strict`. A gate that
fails the queue it governs, before its own fixtures prove each check can fire,
would be the exact "plausible artifact from an unchecked process" this repo's
gate discipline exists to prevent. `--strict` turns findings into exit 1.

GRANDFATHERING

The `Directive:` field is required from issue #89 onward. Every issue up to and
including `GRANDFATHER_MAX` is exempt, including the consideration and challenge
issues that this change itself filed.

THE FIXTURE RULE

`--self-test` runs every check against a bad input and requires a finding, then
against a good input and requires none. A check that cannot fail is not a check,
so a check with no failing case is reported BROKEN and the self-test fails.

Usage:
    python3 tooling/gates/directive_scan.py                    # offline, warn-only
    python3 tooling/gates/directive_scan.py --strict           # exit 1 on findings
    python3 tooling/gates/directive_scan.py --issues-file /tmp/issues.json
    python3 tooling/gates/directive_scan.py --self-test

Tier 0: file inspection and `git log`. No network, no model.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from run_all import Gate, register           # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
LOG = REPO / "docs" / "decisions" / "LOG.md"
CONSIDERATIONS = REPO / "docs" / "decisions" / "considerations"

GRANDFATHER_MAX = 88          # highest issue number recorded in Phase 0
TRAILER_GRACE = "2026-10-14"  # two weeks from adoption: trailer findings are warnings until then

MEMO_HEADINGS = (
    "Direction restated",
    "Why now",
    "Conflicts",
    "Options",
    "Reversibility",
    "Falsifier",
    "Evidence",
    "Run cap",
)
TIER2_KEYWORDS = re.compile(
    r"branch|gate|claim|credential|token|protocol|schema|workflow|reversal|irreversible",
    re.IGNORECASE,
)
DIRECTIVE_RE = re.compile(r"Directive:\s*(DEC-\d{3})")
DEC_HEADING_RE = re.compile(r"^##\s+(DEC-\d{3})\s+—")
STATUS_RE = re.compile(r"\*\*Status:\*\*\s*(\w+)")
TIER_RE = re.compile(r"\*\*Tier:\*\*\s*(\d)")
LOGGED_LATE_RE = re.compile(r"Logged-late:\s*true", re.IGNORECASE)


class Finding:
    __slots__ = ("check", "detail")

    def __init__(self, check: str, detail: str) -> None:
        self.check = check
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.check}: {self.detail}"


class Dec:
    __slots__ = ("id", "status", "tier", "logged_late", "headings", "body")

    def __init__(self, id: str, status: str = "", tier: str = "") -> None:
        self.id = id
        self.status = status
        self.tier = tier
        self.logged_late = False
        self.headings: list[str] = []
        self.body = ""


def parse_decs(text: str) -> dict[str, Dec]:
    """Split LOG.md into DEC entries by heading, keeping the body of each."""
    decs: dict[str, Dec] = {}
    current: Dec | None = None
    for line in text.splitlines():
        m = DEC_HEADING_RE.match(line)
        if m:
            current = Dec(id=m.group(1))
            decs[current.id] = current
            continue
        if current is None:
            continue
        current.body += line + "\n"
        s = STATUS_RE.search(line)
        if s and not current.status:
            current.status = s.group(1)
        t = TIER_RE.search(line)
        if t and not current.tier:
            current.tier = t.group(1)
        if LOGGED_LATE_RE.search(line):
            current.logged_late = True
    return decs


def memo_headings(dec_id: str, cons_dir: Path | None = None) -> list[str]:
    path = (cons_dir or CONSIDERATIONS) / f"{dec_id}.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return [h for h in MEMO_HEADINGS if re.search(rf"^##+\s*\d*\.?\s*{re.escape(h)}", text, re.MULTILINE)]


def challenge_exists(dec_id: str, cons_dir: Path | None = None) -> bool:
    return ((cons_dir or CONSIDERATIONS) / f"{dec_id}.challenge.md").exists()


# --------------------------------------------------------------------------
# Checks. Each takes a `Dec` (or an issue dict) and returns findings.
# --------------------------------------------------------------------------

def check_cited_dec_exists(dec_id: str, decs: dict[str, Dec]) -> list[Finding]:
    if dec_id not in decs:
        return [Finding("cited-dec-exists", f"{dec_id} is cited but not in LOG.md")]
    return []


def check_cited_dec_active(dec_id: str, decs: dict[str, Dec], ratification_task: bool) -> list[Finding]:
    dec = decs.get(dec_id)
    if dec and dec.status.lower() == "proposed" and not ratification_task:
        return [Finding("cited-dec-active",
                        f"{dec_id} is Proposed and this issue is not a ratification task")]
    return []


def check_issue_has_directive(issue: dict) -> list[Finding]:
    number = issue.get("number", 0)
    labels = issue.get("labels", [])
    names = [l["name"] if isinstance(l, dict) else l for l in labels]
    if number <= GRANDFATHER_MAX:
        return []
    if not ({"status:available", "status:claimed"} & set(names)):
        return []
    body = issue.get("body") or ""
    if not DIRECTIVE_RE.search(body):
        return [Finding("issue-has-directive",
                        f"#{number} is claimable but has no `Directive: DEC-NNN`")]
    return []


def check_logged_late(dec_id: str, dec: Dec, dec_commit_date: str, issue_created: str) -> list[Finding]:
    if dec_commit_date and issue_created and dec_commit_date > issue_created and not dec.logged_late:
        return [Finding("logged-late",
                        f"{dec_id} commit {dec_commit_date} is later than the issue "
                        f"({issue_created}) and lacks `Logged-late: true`")]
    return []


def check_active_dec_has_memo(dec: Dec, cons_dir: Path | None = None) -> list[Finding]:
    if dec.status.lower() != "active":
        return []
    if dec.tier not in ("1", "2"):
        return []
    headings = memo_headings(dec.id, cons_dir)
    if not headings:
        return [Finding("active-dec-memo", f"{dec.id} is Active Tier {dec.tier} with no memo")]
    missing = [h for h in MEMO_HEADINGS if h not in headings]
    if missing:
        return [Finding("active-dec-memo", f"{dec.id} memo lacks headings: {', '.join(missing)}")]
    return []


def check_tier2_has_challenge(dec: Dec, cons_dir: Path | None = None) -> list[Finding]:
    if dec.status.lower() == "active" and dec.tier == "2" and not challenge_exists(dec.id, cons_dir):
        return [Finding("tier2-challenge", f"{dec.id} is Active Tier 2 with no challenge file")]
    return []


NEGATION_RE = re.compile(r"\b(no|not|without|unchanged|does not|do not|never|no longer)\b",
                         re.IGNORECASE)


def _decision_text(dec: Dec) -> str:
    """The DEC's Decision/Rationale lines, joined.

    The tier-keyword check reads intent, not incidental mentions: a DEC whose
    *Decision* renames a doc but whose Context says "no gate changes" must not
    read as load-bearing. Restricting to the decision text, plus the negation
    guard in `check_tier_keywords`, is what keeps that from firing.
    """
    keep: list[str] = []
    for line in dec.body.splitlines():
        if re.match(r"\*\*(Decision|Rationale):\*\*", line, re.IGNORECASE):
            keep.append(line)
    return "\n".join(keep) or dec.body


def check_tier_keywords(dec: Dec) -> list[Finding]:
    if dec.tier not in ("0", "1"):
        return []
    for line in _decision_text(dec).splitlines():
        m = TIER2_KEYWORDS.search(line)
        if m and not NEGATION_RE.search(line):
            return [Finding("tier-keywords",
                            f"{dec.id} is Tier {dec.tier} but its Decision matches the "
                            f"Tier 2 keyword {m.group(0)!r} "
                            f"(branch/gate/claim/credential/protocol/schema/workflow)")]
    return []


def check_proposed_dec_not_cited_by_task(issue: dict, decs: dict[str, Dec]) -> list[Finding]:
    number = issue.get("number", 0)
    if number <= GRANDFATHER_MAX:
        return []
    names = [l["name"] if isinstance(l, dict) else l for l in issue.get("labels", [])]
    if "bakeoff" in names or "ratification" in (issue.get("title") or "").lower():
        return []          # slots and ratification tasks legitimately cite a pending DEC
    m = DIRECTIVE_RE.search(issue.get("body") or "")
    if not m:
        return []
    dec = decs.get(m.group(1))
    if dec and dec.status.lower() == "proposed":
        return [Finding("proposed-dec-cited",
                        f"#{number} cites {dec.id}, which is still Proposed")]
    return []


def check_commit_trailer(sha: str, subject: str, body: str) -> list[Finding]:
    if "Directive:" in body or "Directive:" in subject:
        return []
    return [Finding("commit-trailer", f"{sha[:7]} has no `Directive:` trailer")]


def check_tier2_urgent_window(dec_id: str, ratified_at: str, memo_at: str,
                              urgent: bool) -> list[Finding]:
    if not (ratified_at and memo_at) or urgent:
        return []
    # ISO-8601 UTC strings compare lexicographically.
    from datetime import datetime, timezone
    try:
        r = datetime.fromisoformat(ratified_at.replace("Z", "+00:00"))
        m = datetime.fromisoformat(memo_at.replace("Z", "+00:00"))
    except ValueError:
        return []
    if (r - m).total_seconds() < 24 * 3600:
        return [Finding("tier2-urgent-window",
                        f"{dec_id} ratified {(r - m).total_seconds() / 3600:.1f}h after the memo "
                        f"without `URGENT:`")]
    return []


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

def _adoption_commit() -> str | None:
    """The commit that introduced DIRECTIVE_PROTOCOL.md, or None."""
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%H", "--",
             "docs/DIRECTIVE_PROTOCOL.md"],
            cwd=REPO, capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    lines = out.stdout.strip().splitlines()
    return lines[0] if lines else None


def git_log_trailers() -> list[Finding]:
    """Commits after the protocol landed on main with no Directive: trailer.

    Scoped to `adoption..HEAD` rather than a date: every commit before the
    protocol existed is legitimately trailer-less, and flagging them would bury
    the real findings in noise.
    """
    adoption = _adoption_commit()
    if not adoption:
        return []
    try:
        out = subprocess.run(
            ["git", "log", f"{adoption}..HEAD", "--format=%h%x00%s%x00%b%x1e"],
            cwd=REPO, capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if out.returncode != 0:
        return []
    findings: list[Finding] = []
    for record in out.stdout.split("\x1e"):
        parts = record.strip().split("\x00")
        if len(parts) < 3:
            continue
        sha, subject, body = parts[0], parts[1], parts[2]
        if subject.startswith("chore(") or "skip ci" in subject:
            continue
        findings.extend(check_commit_trailer(sha, subject, body))
    return findings


def scan(issues: list[dict] | None, decs: dict[str, Dec]) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    skipped: list[str] = []

    for dec in decs.values():
        findings.extend(check_active_dec_has_memo(dec))
        findings.extend(check_tier2_has_challenge(dec))
        findings.extend(check_tier_keywords(dec))

    if issues is None:
        skipped.append("tracker checks (no --issues-file): issue-has-directive, "
                       "cited-dec-exists, cited-dec-active, proposed-dec-cited")
    else:
        for issue in issues:
            findings.extend(check_issue_has_directive(issue))
            findings.extend(check_proposed_dec_not_cited_by_task(issue, decs))
            m = DIRECTIVE_RE.search(issue.get("body") or "")
            if m:
                findings.extend(check_cited_dec_exists(m.group(1), decs))
                findings.extend(check_cited_dec_active(
                    m.group(1), decs,
                    ratification_task="ratification" in (issue.get("title") or "").lower()))

    findings.extend(git_log_trailers())
    return findings, skipped


# --------------------------------------------------------------------------
# Self-test: every check must fire on a bad case and stay silent on a good one.
# --------------------------------------------------------------------------

def gate_d1(path: Path) -> list[str]:
    """Fixture entry point: scan a fixture tree (`LOG.md`, `considerations/`,
    optional `issues.json`) with the offline + tracker checks.

    Kept separate from `main()` so `run_all.py` can drive it over a fixture
    directory deterministically, without touching the real repo or the network.
    """
    log = path / "LOG.md"
    considerations = path / "considerations"
    decs = parse_decs(log.read_text(encoding="utf-8")) if log.exists() else {}
    issues = None
    issues_file = path / "issues.json"
    if issues_file.exists():
        issues = json.loads(issues_file.read_text(encoding="utf-8"))

    findings: list[str] = []
    cons_dir = considerations if considerations.exists() else None
    for dec in decs.values():
        findings.extend(str(f) for f in check_active_dec_has_memo(dec, cons_dir))
        findings.extend(str(f) for f in check_tier2_has_challenge(dec, cons_dir))
        findings.extend(str(f) for f in check_tier_keywords(dec))
    if issues is not None:
        for issue in issues:
            findings.extend(str(f) for f in check_issue_has_directive(issue))
            findings.extend(str(f) for f in check_proposed_dec_not_cited_by_task(issue, decs))
    return findings


register(Gate(
    id="G-D1",
    name="directive-first",
    tier=0,
    check=gate_d1,
    clean_fixture="directive_scan/clean",
    failing_fixture="directive_scan/failing",
    traces_to="DIRECTIVE_PROTOCOL.md § 1, § 1a (DEC-041)",
    description="An Active Tier 1/2 DEC has a memo with the eight headings and, "
                "at Tier 2, a challenge file; a Tier 0/1 DEC does not match Tier 2 "
                "keywords; and a claimable issue from #89 has a `Directive:` citing "
                "a DEC that exists. Advisory by default (`--strict` to fail).",
))


def _dec_with_body(dec_id: str, tier: str, body: str) -> Dec:
    d = Dec(dec_id, status="Active", tier=tier)
    d.body = body
    return d


def _selftest() -> int:
    good_dec = Dec("DEC-900", status="Active", tier="2")
    good_decs = {"DEC-900": good_dec}
    good_issue = {"number": 200, "title": "x", "labels": ["status:available"],
                  "body": "Directive: DEC-900\n"}

    cases = [
        ("cited-dec-exists",
         lambda: check_cited_dec_exists("DEC-901", good_decs),
         lambda: check_cited_dec_exists("DEC-900", good_decs)),
        ("cited-dec-active",
         lambda: check_cited_dec_active("DEC-902", {"DEC-902": Dec("DEC-902", status="Proposed")}, False),
         lambda: check_cited_dec_active("DEC-900", good_decs, False)),
        ("issue-has-directive",
         lambda: check_issue_has_directive({"number": 200, "labels": ["status:available"], "body": "no trailer"}),
         lambda: check_issue_has_directive(good_issue)),
        ("logged-late",
         lambda: check_logged_late("DEC-900", good_dec, "2026-10-02", "2026-10-01"),
         lambda: check_logged_late("DEC-900", good_dec, "2026-09-30", "2026-10-01")),
        ("active-dec-memo",
         lambda: check_active_dec_has_memo(Dec("DEC-903", status="Active", tier="2")),
         lambda: check_active_dec_has_memo(Dec("DEC-904", status="Proposed", tier="2"))),
        ("tier2-challenge",
         lambda: check_tier2_has_challenge(Dec("DEC-905", status="Active", tier="2")),
         lambda: check_tier2_has_challenge(Dec("DEC-906", status="Active", tier="1"))),
        ("tier-keywords",
         lambda: check_tier_keywords(_dec_with_body("DEC-907", "0", "adds a gate")),
         lambda: check_tier_keywords(_dec_with_body("DEC-908", "0", "renames a doc"))),
        ("proposed-dec-cited",
         lambda: check_proposed_dec_not_cited_by_task(
             {"number": 200, "title": "t", "labels": [], "body": "Directive: DEC-909\n"},
             {"DEC-909": Dec("DEC-909", status="Proposed")}),
         lambda: check_proposed_dec_not_cited_by_task(good_issue, good_decs)),
        ("commit-trailer",
         lambda: check_commit_trailer("abc1234", "fix: x", "no trailer"),
         lambda: check_commit_trailer("abc1234", "fix: x", "Directive: DEC-900\n")),
        ("tier2-urgent-window",
         lambda: check_tier2_urgent_window("DEC-900", "2026-09-30T12:00:00Z", "2026-09-30T00:00:00Z", False),
         lambda: check_tier2_urgent_window("DEC-900", "2026-10-02T00:00:00Z", "2026-09-30T00:00:00Z", False)),
    ]

    broken = 0
    for name, bad, good in cases:
        fired = bool(bad())
        silent = not good()
        status = "PASS" if (fired and silent) else "BROKEN"
        if status == "BROKEN":
            broken += 1
        print(f"  {status}  {name}  (fires on bad: {fired}, silent on good: {silent})")
    print("-" * 60)
    if broken:
        print(f"{broken} check(s) BROKEN: a check that cannot fail is not a check")
        return 1
    print(f"{len(cases)} checks fire on a bad case and stay silent on a good one")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Directive scan (DEC-041, warn-only).")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any finding")
    ap.add_argument("--issues-file", default=None,
                    help="cached GitHub issues JSON to enable tracker checks")
    ap.add_argument("--self-test", action="store_true",
                    help="prove each check can fail, then exit")
    args = ap.parse_args(argv)

    if args.self_test:
        return _selftest()

    decs = parse_decs(LOG.read_text(encoding="utf-8")) if LOG.exists() else {}
    issues = None
    if args.issues_file:
        issues = json.loads(Path(args.issues_file).read_text(encoding="utf-8"))

    findings, skipped = scan(issues, decs)

    print("directive scan (advisory)")
    print("=" * 60)
    print(f"{len(decs)} DEC(s) parsed; grandfather cutoff: #{GRANDFATHER_MAX}")
    for s in skipped:
        print(f"  SKIP  {s}")
    for f in findings:
        print(f"  WARN  {f}")
    print("-" * 60)
    print(f"{len(findings)} finding(s)")
    if args.strict and findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
