"""G-R2 failing fixture: declares model-free but loads a model.

**Model:** none
**Inputs:** fixture prompt sets.
**Question:** does a false model-free declaration still fail?
**Null:** fixture null model.
**Correction:** fixture correction.
**Issue:** #75 (fixture only).
"""

from transformers import AutoModelForCausalLM


def load(model_id):
    # Deliberately unpinned: this fixture's whole point is an unguarded
    # from_pretrained call (see module docstring). Suppress bandit B615
    # rather than pin, because pinning would be a no-op on a fixture
    # that never runs.
    return AutoModelForCausalLM.from_pretrained(model_id)  # nosec B615
