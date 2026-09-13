"""Action payload hashing (BD_v2.md §7: "Approval is bound to the exact
payload hash. Any payload change invalidates prior approval.").

Both apps/api (checking an approval request against the current action) and
apps/ai_atlas (freezing the payload at PROPOSE_ACTION) must compute this
hash identically — hence a single shared function rather than each side
reimplementing `hashlib.sha256(json.dumps(...))`.
"""

from __future__ import annotations

import hashlib

from atlasai_domain.contracts.actions import ActionPayload


def hash_payload(payload: ActionPayload) -> str:
    return hashlib.sha256(payload.canonical_json().encode("utf-8")).hexdigest()
