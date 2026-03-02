from keon_sdk import DecisionReceipt, TrustBundle


def test_decision_receipt_verify_checks_bundle_membership() -> None:
    receipt = DecisionReceipt(
        {
            "receipt_id": "dr-1",
            "tenant_id": "tenant-1",
            "signer_kid": "kid-1",
        }
    )
    bundle = TrustBundle(
        {
            "tenants": [
                {
                    "tenant_id": "tenant-1",
                    "keys": [{"kid": "kid-1"}],
                }
            ]
        }
    )

    result = receipt.verify(bundle)

    assert result.is_valid is True
    assert result.key_authorized is True

