# Domain Leader Study — a11oy-net (proof registry)

OUROBOROS phase-3, cohort-01 tranche-2. PROPOSE-ONLY study card: documentation only, no production change in this PR.

## Domain leaders studied
| Leader | What they have | Key sources |
| --- | --- | --- |
| Sigstore Rekor | Append-only transparency log with public verifiable inclusion proofs, checkpoint/signed-tree-head model, REST API over Merkle leaf entries | github.com/sigstore/architecture-docs/blob/main/rekor-spec.md; docs.sigstore.dev/logging/overview |
| Certificate Transparency (RFC 6962 lineage) | The original gossip-auditable append-only log design Rekor inherits: inclusion proofs, consistency proofs, third-party monitors | via Rekor spec lineage |

## What the leaders do better
- Entry inclusion is independently checkable: any third party can verify an inclusion proof against a checkpoint. The checkpoint itself (root and signature) is still an operator trust point unless an independently trusted witness or gossip network validates it, so proofs shift trust from the operator's current view to a pinned, witnessed checkpoint rather than removing operator trust.
- Consistency proofs let an auditor verify the log stayed append-only between two given checkpoints: this is mutation detection between trusted checkpoints, not a global never-rewrote guarantee (that stronger property additionally requires continuously persisted, cross-gossiped checkpoints and third-party monitors, per Certificate Transparency practice). Exactly the property class a proof registry needs for receipts, stated at its honest strength.
- Monitoring is decentralized: anyone can run a monitor, so log misbehavior is detectable, not preventable. Detection over prevention.

## Absorb actions (proposed, NOT implemented in this PR)
- [ ] Add an inclusion-proof field to every registry entry commit: leaf hash + audit path + tree size, plus the full signed checkpoint (origin, tree size, root hash, signature) or an authenticated reference to it, so a consumer can recompute the root and verify offline that it matches the signed checkpoint rather than re-trusting the operator's view.
- [ ] Add a consistency-check utility that fails closed when a new registry snapshot is not a superset of the previous one.
- [ ] Document the registry's threat model using Rekor's spec: what a malicious log operator could do, and which proof catches it.
- [ ] Emit a signed checkpoint (tree head) per batch so consumers can pin and verify instead of re-trusting.

## Sources
- Rekor spec: https://github.com/sigstore/architecture-docs/blob/main/rekor-spec.md
- Rekor docs: https://docs.sigstore.dev/logging/overview/
- sigstore/rekor: https://github.com/sigstore/rekor
