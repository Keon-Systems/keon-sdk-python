# Keon SDK Python — Release Notes
## v1.0.0 — 2026-02-22

---

## What Shipped

### `subjectHash` Required on `DecideRequest` (Phase 5)
`DecideRequest` now requires `subjectHash` (alias: `subjectHash`):

```python
DecideRequest(
    correlationId="t:my-tenant|c:<uuidv7>",
    tenantId="my-tenant",
    actorId="agent-1",
    action="EXECUTE_WORKFLOW",
    resourceType="workflow",
    resourceId="wf-123",
    subjectHash="<sha256 hex of canonical subject payload>",
)
```

**Empty or absent `subjectHash` → `ValidationError` at construction.** Fail-closed by design.

`subjectHash` MUST be the SHA-256 hex digest of the canonical (JCS) subject payload being governed. This binds the policy decision to the specific content being authorized.

### Schema Drift Tripwire Updated
`_DECIDE_FIELDS_HASH` updated from `6a8c75b57593cd19` → `5c7ae3e6d532d49a`.

Any future unapproved change to `DecideRequest` required fields will trip CI.

---

## Previously Shipped (Sealed at v1.0.0)

- **KEON-SDK-SENTINEL-1a**: `correlationId` required; malformed → rejected; `tenantId` + `actorId` mandatory
- **KEON-SDK-SENTINEL-1b**: `DecisionReceipt` schema strict; `receiptId` pattern `^dr-<uuidv7>`
- **KEON-SDK-SENTINEL-1c**: Timeout → `NetworkError` (fail-closed); gateway never allows on failure

---

## Breaking Changes

| Change | Required Action |
|--------|----------------|
| `subjectHash` now required on `DecideRequest` | Compute SHA-256 of canonical subject content and pass as `subjectHash` |

**All callers that construct `DecideRequest` must be updated.** Missing `subjectHash` will raise `ValidationError` at runtime.

---

## Computing `subjectHash`

```python
import hashlib, json

def compute_subject_hash(payload: dict) -> str:
    """JCS canonical hash of the subject payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

---

## Known Limitations

- `subjectHash` validation is structural only (non-empty string). Hash format (hex, length) is not enforced at SDK level — Keon Runtime validates the binding server-side.

---

## Verify Quickly

```bash
pytest tests/test_keon_sentinels.py -q -m sentinel
```

Expected: all sentinels green including new `subjectHash` tests.

---

## Tags

| Tag | Commit |
|-----|--------|
| `keon-sdk-python-v1.0.0` | `3e20e01` |
| `keon-sdk-python-v1.0.0-rc1` | `3e20e01` |
| `keon-sdk-sentinels-v1.0.0` | sealed prior |
