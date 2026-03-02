from keon_sdk import verify_caes


def test_quickstart_import_exports_verify_caes() -> None:
    assert callable(verify_caes)

