# keon-sdk-python — Architecture Sentinels

**Status:** SEALED
**Scope:** Architecture + Contract Guardrails
**Rule:** No merge to main with sentinel failures.
**Layer:** Policy SDK — enforces that policy authority is sovereign and cannot be weakened.

---

## What these sentinels protect

Sentinels are non-negotiable guardrails that prevent architectural drift and authority weakening.
They are designed to fail closed.

## Required Suites

- `pytest -q` must include the sentinel file.
- CI must block merges if sentinel suites are skipped or fail.
- The `sentinels` CI job gates `test`, which gates `lint`.

## Failure Philosophy

- **Fail-closed:** If authority cannot be verified, the system must refuse to proceed.
- **No silent downgrade:** Contract drift must be explicit and reviewed.
- **No bypass paths:** Forbidden shortcuts are treated as defects, not optimizations.

## Sentinel Inventory

> Update this list intentionally. Removing or weakening sentinels requires doctrine review.

**Guarantee:** DecideRequest + DecisionReceipt strict, timeout → `NetworkError`, policy authority cannot silently weaken.

| File | ID | Invariant |
|------|----|-----------| 
| `test_keon_sentinels.py` | KEON-SDK-1a | `DecideRequest` without `correlationId` fails at construction |
| `test_keon_sentinels.py` | KEON-SDK-1a | Malformed `correlationId` (non-uuidv7) rejected at construction |
| `test_keon_sentinels.py` | KEON-SDK-1a | `tenantId` and `actorId` both mandatory — absent cases fail |
| `test_keon_sentinels.py` | KEON-SDK-1b | `DecisionReceipt` without `receiptId` fails at construction |
| `test_keon_sentinels.py` | KEON-SDK-1b | `receiptId` not matching `^dr-<uuidv7>` rejected |
| `test_keon_sentinels.py` | KEON-SDK-1b | `DecisionReceipt` without `decision` field fails |
| `test_keon_sentinels.py` | KEON-SDK-1c | Gateway timeout → `NetworkError`; never silently allows on failure |
| `test_keon_sentinels.py` | DRIFT-1 | `DecideRequest` required-field set matches approved hash (no silent additions/removals) |
| `test_keon_sentinels.py` | DRIFT-2 | `DecisionReceipt` required-field set matches approved hash (no silent additions/removals) |

---

## How to Run

```bash
cd keon-sdk-python
pytest -q
```

---

## Drift Tripwires

`DRIFT-1` and `DRIFT-2` hash the set of required fields in `DecideRequest` and `DecisionReceipt` at test time using `model_fields`. If any required field is added or removed without updating the stored hash, CI fails.

To update after an approved schema change:
1. Make the intentional change to the Pydantic model.
2. Compute the new hash:
   ```python
   python -c "
   import hashlib, json
   from keon_sdk.contracts import DecideRequest
   fields = sorted(n for n, i in DecideRequest.model_fields.items() if i.is_required())
   print(hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()[:16])
   "
   ```
3. Update `_DECIDE_FIELDS_HASH` or `_RECEIPT_FIELDS_HASH` in `test_keon_sentinels.py`.
4. Commit: `sentinel(drift): approve <what changed> — <reason>`.

---

## Seal Record

- **Tag:** `keon-sdk-sentinels-v1.0.0`
- **Commit:** `6da04940a6e109db6c57fd12583d5ac9cc67ede2`
- **Date:** 2026-02-22

