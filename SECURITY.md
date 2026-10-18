# Security Policy

## Supported versions

Ephapse is a research proof-of-concept, not a deployed service. Only the
current `main` branch is supported; older commits receive no security fixes.

## Reporting a vulnerability

Please report suspected vulnerabilities privately — do not open a public issue.

- Email **pda728@gmail.com** with the details.
- If GitHub's private vulnerability reporting is enabled on this repository
  (Security → Report a vulnerability), you may use that instead — it is not
  enabled at the time of writing, so email is the reliable path.

Please include: a description of the issue, the affected file or component, the
commit you tested, and reproduction steps or a proof of concept.

## What to expect

This is a single-maintainer project, so response times are best-effort:

| Stage | Target |
|---|---|
| Acknowledgement | within 7 days |
| Initial assessment | within 14 days |
| Fix or mitigation plan | as soon as a fix is available |

We will credit reporters in the advisory unless you ask to remain anonymous.

## Scope

In scope: the code and configuration in this repository on `main` — the probing
and tooling code under `program/`, `tooling/`, and `experiments/`, and the GitHub
Actions workflows under `.github/workflows/`.

Out of scope: upstream issues in the probed models and their weights, in the
`transformer-lens` / `sae-lens` packages, and in any hosted probing API
(Neuronpedia, nnsight/NDIF) — report those upstream. Any third-party dependency
vulnerability already covered by an upstream advisory is out of scope too,
though we will happily take a report that Dependabot missed.
