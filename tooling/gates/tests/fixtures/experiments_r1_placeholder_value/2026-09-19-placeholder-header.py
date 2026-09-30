"""G-R1 failing fixture (issue #86): all six labels present, values are stubs.

Before #86 G-R1 checked field *presence*, so this file passed -- the six labels
are all there. The values are placeholders, which is the state a file reaches
when the header is copied and not filled in: a plausible artifact from an
unchecked process, and exactly what the gate exists to catch. It must be
reported as present-but-unfilled, not as a clean header.

**Model:** pythia-70m-deduped, fp32, CPU.
**Inputs:** TBD
**Question:** ?
**Null:** none.
**Correction:** n/a
**Issue:** #86 (fixture only).
"""

MODEL = "pythia-70m-deduped"
