# Keon Python SDK

> *Part of the [Keon Governance Platform](https://github.com/Keon-Systems).*
> *Documentation: [keon-docs](https://github.com/Keon-Systems/keon-docs)*
> *Website: [keon.systems](https://keon.systems)*

---

> **Powered by [OMEGA](https://github.com/omega-brands). Governed by [Keon](https://github.com/Keon-Systems).**

**Team Claude deliverable** — Thin, safe-by-default Python client for Keon Runtime.

Governance-first SDK with strict invariants, automatic retries, and structured error handling.

## 🎯 Features

- **Strict validation**: CorrelationId canonical form enforced
- **Receipt requirement**: Execute REQUIRES DecisionReceiptId (hard fail if absent)
- **Automatic retries**: Transient failures retry with exponential backoff
- **Structured errors**: Typed exceptions with machine-readable codes
- **Type-safe**: Full Pydantic v2 contracts with validation
- **Async-first**: Built on httpx for modern async Python

## 📦 Installation

```bash
pip install keon-sdk
```

### Development

```bash
pip install keon-sdk[dev]
```

## 🚀 Quick Start

```python
from keon_sdk import KeonClient

async with KeonClient(
    base_url="https://api.keon.systems/runtime/v1",
    api_key="your-api-key",
) as client:
    # Request decision
    receipt = await client.decide(
        tenant_id="tenant-123",
        actor_id="user-456",
        action="execute_workflow",
        resource_type="workflow",
        resource_id="workflow-789",
        context={"environment": "production"},
    )

    # Execute if allowed
    if receipt.decision == "allow":
        result = await client.execute(
            receipt=receipt,
            action="execute_workflow",
            parameters={
                "workflowId": "workflow-789",
                "inputs": {"param1": "value1"},
            },
        )
        print(f"Execution ID: {result.execution_id}")
    else:
        print(f"Denied: {receipt.reason}")
```

## 📚 Core API

### KeonClient

Main entry point for SDK.

```python
client = KeonClient(
    base_url="https://api.keon.systems/runtime/v1",
    api_key="your-api-key",  # Optional: use api_key OR bearer_token
    bearer_token="your-jwt",  # Optional: JWT bearer token
    retry_policy=RetryPolicy.default(),  # Optional: custom retry policy
    timeout=30.0,  # Optional: request timeout in seconds
)
```

### decide()

Request a policy decision before execution.

```python
receipt = await client.decide(
    tenant_id="tenant-123",
    actor_id="user-456",
    action="execute_workflow",
    resource_type="workflow",
    resource_id="workflow-789",
    context={"environment": "production"},  # Optional
    correlation_id="t:tenant-123|c:...",  # Optional: auto-generated if not provided
)

# receipt.decision: "allow" | "deny"
# receipt.receipt_id: "dr-..."
# receipt.reason: Human-readable explanation
```

**Returns:** `DecisionReceipt`

**Raises:**
- `InvalidCorrelationIdError`: CorrelationId format invalid
- `ValidationError`: Request validation failed
- `NetworkError`: Connection/timeout issues
- `ServerError`: 5xx server errors

### execute()

Execute an action under governance.

**REQUIRES** a `DecisionReceipt` from `decide()`. Hard fails without receipt.

```python
result = await client.execute(
    receipt=receipt,  # REQUIRED: from decide()
    action="execute_workflow",
    parameters={  # Optional: action-specific parameters
        "workflowId": "workflow-789",
        "inputs": {"param1": "value1"},
    },
)

# result.execution_id: "exec-..."
# result.status: "completed" | "running" | "failed" | etc.
# result.result: Action-specific result data
```

**Returns:** `ExecutionResult`

**Raises:**
- `MissingReceiptError`: Receipt not provided
- `InvalidReceiptError`: Receipt invalid or expired
- `ExecutionDeniedError`: Policy denied execution
- `NetworkError`: Connection/timeout issues
- `ServerError`: 5xx server errors

### decide_and_execute()

Convenience method: decide + execute in one call.

```python
result = await client.decide_and_execute(
    tenant_id="tenant-123",
    actor_id="user-456",
    action="execute_workflow",
    resource_type="workflow",
    resource_id="workflow-789",
    parameters={"inputs": {"param1": "value1"}},
    context={"environment": "production"},
)
```

Automatically handles decide → execute flow. Raises `ExecutionDeniedError` if policy denies.

## 🔒 Strict Invariants

### 1. CorrelationId is Mandatory

Format: `t:<TenantId>|c:<uuidv7>`

```python
# Valid
"t:tenant-123|c:01932b3c-4d5e-7890-abcd-ef1234567890"

# Invalid - will raise InvalidCorrelationIdError
"invalid-format"
"t:tenant-123:c:01932b3c-4d5e-7890-abcd-ef1234567890"  # Wrong separator
"t:tenant-123|c:01932b3c-4d5e-4890-abcd-ef1234567890"  # UUIDv4, not v7
```

Auto-generated if not provided to `decide()`.

### 2. Execute Requires Receipt

```python
# ✅ Correct
receipt = await client.decide(...)
if receipt.decision == "allow":
    result = await client.execute(receipt=receipt, action="...")

# ❌ Wrong - raises MissingReceiptError
await client.execute(receipt=None, action="...")

# ❌ Wrong - raises ExecutionDeniedError
denied_receipt = await client.decide(...)  # decision = "deny"
await client.execute(receipt=denied_receipt, action="...")
```

### 3. TenantId and ActorId Required

All operations require tenant and actor identification for audit and attribution.

## 🔄 Retry Policy

Safe-by-default retries for transient failures.

### Default Policy

```python
RetryPolicy.default()
# - Max attempts: 3
# - Backoff: 1s, 2s, 4s (exponential)
# - Retries: NetworkError, ServerError (5xx), RateLimitError
# - No retry: ValidationError, ExecutionDeniedError, 4xx (except 429)
```

### Custom Policy

```python
client = KeonClient(
    base_url="...",
    retry_policy=RetryPolicy(
        max_attempts=5,
        min_wait_seconds=0.5,
        max_wait_seconds=30.0,
        multiplier=2.0,
    ),
)
```

### No Retry

```python
client = KeonClient(
    base_url="...",
    retry_policy=RetryPolicy.no_retry(),
)
```

### Aggressive Retry

```python
client = KeonClient(
    base_url="...",
    retry_policy=RetryPolicy.aggressive(),
)
```

## ❌ Error Handling

All errors inherit from `KeonError`.

```python
from keon_sdk import (
    KeonError,
    ValidationError,
    InvalidCorrelationIdError,
    MissingReceiptError,
    InvalidReceiptError,
    ExecutionDeniedError,
    NetworkError,
    ServerError,
    RateLimitError,
    RetryExhaustedError,
)

try:
    result = await client.decide_and_execute(...)
except ExecutionDeniedError as e:
    print(f"Policy denied: {e.message}")
    print(f"Receipt ID: {e.details['receiptId']}")
except NetworkError as e:
    print(f"Network issue: {e.message}")
except KeonError as e:
    print(f"Keon error: {e.code} - {e.message}")
```

### Error Structure

All errors have:
- `message`: Human-readable message
- `code`: Machine-readable error code
- `details`: Additional context dict

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=keon_sdk --cov-report=html

# Run specific test
pytest tests/test_correlation_id.py -v

# Type checking
mypy keon_sdk

# Linting
ruff check keon_sdk
black --check keon_sdk
```

## 🏗️ Architecture

```
keon_sdk/
├── client.py          # KeonClient - main SDK entry point
├── gateway.py         # RuntimeGateway protocol
├── http_gateway.py    # HTTP implementation with retries
├── contracts.py       # Pydantic models (from keon-contracts)
├── errors.py          # Typed exceptions
└── retry.py           # Retry policy configuration
```

### Gateway Abstraction

The SDK uses a `RuntimeGateway` protocol for flexibility:

```python
from keon_sdk import KeonClient, RuntimeGateway

# Custom gateway implementation
class MyCustomGateway(RuntimeGateway):
    async def decide(self, request):
        # Custom implementation
        pass

    async def execute(self, request):
        # Custom implementation
        pass

client = KeonClient(gateway=MyCustomGateway())
```

## 📋 Requirements

- Python >= 3.11
- httpx >= 0.27.0
- pydantic >= 2.0.0
- tenacity >= 8.0.0

## 🔗 Related

- **Keon Contracts**: `keon-contracts` (OpenAPI source of truth)
- **Keon Runtime**: Execution platform
- **TypeScript SDK**: `@keon/sdk`

## 📄 License

Apache License 2.0 - See LICENSE file

---

**Version:** 1.0.0
**Tag:** `keon-sdk-python-v1.0.0`
**Branch:** `team-claude/keon-sdk-python-v1`
**Team:** Claude 🧠 (Python SDK)
