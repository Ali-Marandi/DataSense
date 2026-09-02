import pandas as pd

from core.security import DataSecurity


def test_encrypt_column_does_not_mutate_input() -> None:
    frame = pd.DataFrame({"id": [1, 2], "secret": ["alpha", "beta"]})
    original = frame.copy(deep=True)
    security = DataSecurity()
    encrypted, error = security.encrypt_column(frame, "secret")
    assert error is None
    pd.testing.assert_frame_equal(frame, original)
    assert encrypted["secret"].tolist() != original["secret"].tolist()


def test_encrypt_then_decrypt_round_trip_with_same_key() -> None:
    frame = pd.DataFrame({"secret": ["alpha", "beta"]})
    security = DataSecurity()
    encrypted, error = security.encrypt_column(frame, "secret")
    assert error is None
    restored, error = security.decrypt_column(encrypted, "secret")
    assert error is None
    pd.testing.assert_series_equal(restored["secret"], frame["secret"], check_names=True)


def test_wrong_key_fails_closed() -> None:
    frame = pd.DataFrame({"secret": ["alpha"]})
    encrypted, error = DataSecurity().encrypt_column(frame, "secret")
    assert error is None
    restored, error = DataSecurity().decrypt_column(encrypted, "secret")
    assert restored.equals(encrypted)
    assert error is not None


def test_missing_column_is_reported() -> None:
    frame = pd.DataFrame({"id": [1]})
    encrypted, error = DataSecurity().encrypt_column(frame, "missing")
    assert encrypted.equals(frame)
    assert error is not None
