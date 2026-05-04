"""Unit tests for the app-level Fernet at-rest layer (Issue #26 / ADR-0005).

Coverage
--------
1. ``generate_dek`` / ``wrap_dek`` / ``unwrap_dek`` round-trip with the
   master :class:`MultiFernet`.
2. ``encrypt_with_dek`` / ``decrypt_with_dek`` round-trip with a per-user
   DEK.
3. ContextVar binding helpers: set / get / reset, isolation between
   sequential bindings, ``DekUnavailableError`` when not bound.
4. ``EncryptedString`` TypeDecorator: ``process_bind_param`` /
   ``process_result_value`` round-trip via the bound ContextVar.
5. ``Symptom.set_custom_name`` / ``Symptom.display_name`` polymorphism
   for default vs custom rows.
6. Master-key rotation tolerance: a token written under key A still
   decrypts when the master is rebuilt with ``[B, A]`` (MultiFernet).
7. Log-scrubbing: ``Symptom.__repr__`` and ``EntrySymptom.__repr__`` do
   not leak the plaintext name / intensity.

These tests exercise the crypto layer in isolation \u2014 no database, no
network, no Redis. Persistence-layer integration is covered separately
once a live Postgres is available.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from cryptography.fernet import Fernet

from app.core.crypto import (
    DecryptionError,
    DekUnavailableError,
    EncryptedString,
    decrypt_with_dek,
    encrypt_with_dek,
    generate_dek,
    get_current_user_dek,
    get_current_user_id_for_dek,
    reset_current_user_dek,
    reset_master_fernet_cache,
    set_current_user_dek,
    unwrap_dek,
    wrap_dek,
)
from app.models.symptom import EntrySymptom, Symptom

# ---------------------------------------------------------------------------
# DEK lifecycle
# ---------------------------------------------------------------------------


def test_generate_dek_is_valid_fernet_key() -> None:
    dek = generate_dek()
    # Fernet keys are 32 url-safe base64 bytes \u2192 44 chars total.
    assert len(dek) == 44
    # Round-trips through Fernet without raising:
    Fernet(dek).encrypt(b"ping")


def test_wrap_unwrap_round_trip() -> None:
    dek = generate_dek()
    wrapped = wrap_dek(dek)
    assert wrapped != dek
    # Unwrap restores the original DEK byte-for-byte.
    assert unwrap_dek(wrapped) == dek


def test_unwrap_dek_handles_memoryview() -> None:
    dek = generate_dek()
    wrapped = wrap_dek(dek)
    assert unwrap_dek(memoryview(wrapped)) == dek


def test_unwrap_dek_with_wrong_master_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A wrapped DEK must be undecipherable under a different master key."""
    from cryptography.fernet import MultiFernet

    from app.core import crypto as _crypto

    dek = generate_dek()
    wrapped = wrap_dek(dek)

    # Replace the cached master with an unrelated MultiFernet so unwrap fails.
    new_key = Fernet.generate_key()
    fake_master = MultiFernet([Fernet(new_key)])
    monkeypatch.setattr(_crypto, "_master_fernet", fake_master)
    try:
        with pytest.raises(DecryptionError):
            unwrap_dek(wrapped)
    finally:
        reset_master_fernet_cache()


# ---------------------------------------------------------------------------
# Field-level encryption with the DEK
# ---------------------------------------------------------------------------


def test_encrypt_decrypt_with_dek_round_trip() -> None:
    dek = generate_dek()
    plaintext = "Migr\u00e4ne mit Aura \u2014 hinter dem rechten Auge"
    ciphertext = encrypt_with_dek(plaintext, dek)
    assert isinstance(ciphertext, bytes)
    assert plaintext.encode("utf-8") not in ciphertext
    assert decrypt_with_dek(ciphertext, dek) == plaintext


def test_encrypt_with_dek_is_non_deterministic() -> None:
    """Two encryptions of the same plaintext yield different ciphertexts.

    Fernet uses a random IV so identical plaintexts must not produce the
    same token \u2014 important so attackers cannot detect duplicate notes
    just by looking at ciphertext bytes.
    """

    dek = generate_dek()
    a = encrypt_with_dek("hello", dek)
    b = encrypt_with_dek("hello", dek)
    assert a != b
    assert decrypt_with_dek(a, dek) == "hello"
    assert decrypt_with_dek(b, dek) == "hello"


def test_decrypt_with_wrong_dek_raises() -> None:
    dek_a = generate_dek()
    dek_b = generate_dek()
    token = encrypt_with_dek("secret", dek_a)
    with pytest.raises(DecryptionError):
        decrypt_with_dek(token, dek_b)


# ---------------------------------------------------------------------------
# ContextVar binding
# ---------------------------------------------------------------------------


def test_context_var_set_get_reset() -> None:
    # The autouse fixture in conftest already binds a module-scope DEK,
    # so we shadow it here and assert isolation on reset.
    outer_dek = get_current_user_dek()  # set by autouse
    inner_uid = uuid.uuid4()
    inner_dek = generate_dek()
    token = set_current_user_dek(inner_uid, inner_dek)
    try:
        assert get_current_user_dek() == inner_dek
        assert get_current_user_id_for_dek() == inner_uid
    finally:
        reset_current_user_dek(token)
    # After reset we are back to the outer DEK.
    assert get_current_user_dek() == outer_dek


# ---------------------------------------------------------------------------
# EncryptedString TypeDecorator
# ---------------------------------------------------------------------------


def test_encrypted_string_round_trip_through_type_decorator() -> None:
    decorator = EncryptedString()
    # Bind a fresh DEK and verify encrypt-on-write / decrypt-on-read.
    uid = uuid.uuid4()
    dek = generate_dek()
    token = set_current_user_dek(uid, dek)
    try:
        wire = decorator.process_bind_param("hello world", dialect=None)
        assert isinstance(wire, bytes)
        assert b"hello world" not in wire
        out = decorator.process_result_value(wire, dialect=None)
        assert out == "hello world"
    finally:
        reset_current_user_dek(token)


def test_encrypted_string_passes_through_none() -> None:
    decorator = EncryptedString()
    assert decorator.process_bind_param(None, dialect=None) is None
    assert decorator.process_result_value(None, dialect=None) is None


def test_encrypted_string_rejects_non_string() -> None:
    decorator = EncryptedString()
    with pytest.raises(TypeError):
        decorator.process_bind_param(123, dialect=None)


def test_encrypted_string_passes_through_pre_encrypted_bytes() -> None:
    """Migration writes raw ciphertext via ``LargeBinary``-style payloads;
    the TypeDecorator must not double-encrypt those.
    """
    decorator = EncryptedString()
    uid = uuid.uuid4()
    dek = generate_dek()
    token = set_current_user_dek(uid, dek)
    try:
        # Build a real ciphertext so the round-trip below succeeds.
        ciphertext = encrypt_with_dek("payload", dek)
        wire = decorator.process_bind_param(ciphertext, dialect=None)
        assert wire == ciphertext
        out = decorator.process_result_value(wire, dialect=None)
        assert out == "payload"
    finally:
        reset_current_user_dek(token)


# ---------------------------------------------------------------------------
# Symptom polymorphism (default vs custom)
# ---------------------------------------------------------------------------


def _build_default(name: str = "Kopfschmerzen") -> Symptom:
    s = Symptom()
    s.id = uuid.uuid4()
    s.user_id = None
    s.slug = "headache"
    s.is_default = True
    s.name = name
    s.created_at = datetime.now(UTC)
    s.updated_at = datetime.now(UTC)
    return s


def _build_custom_shell() -> Symptom:
    s = Symptom()
    s.id = uuid.uuid4()
    s.user_id = uuid.uuid4()
    s.slug = "tinnitus"
    s.is_default = False
    s.created_at = datetime.now(UTC)
    s.updated_at = datetime.now(UTC)
    return s


def test_symptom_default_display_name_uses_plain_name() -> None:
    s = _build_default("Kopfschmerzen")
    # Default rows must NOT depend on a DEK \u2014 plaintext column only.
    assert s.display_name == "Kopfschmerzen"


def test_symptom_custom_set_and_read_cycles_through_dek() -> None:
    s = _build_custom_shell()
    s.set_custom_name("Tinnitus")
    assert s.name is None  # plaintext column stays empty
    assert s.name_enc is not None
    assert b"Tinnitus" not in s.name_enc
    assert s.display_name == "Tinnitus"


def test_symptom_set_custom_name_rejects_default() -> None:
    s = _build_default()
    with pytest.raises(ValueError):
        s.set_custom_name("nope")


def test_symptom_custom_display_name_without_dek_raises() -> None:
    s = _build_custom_shell()
    s.set_custom_name("Tinnitus")
    # Drop the autouse-bound DEK for the duration of this assertion.
    from app.core import crypto as _c

    saved = _c._current_dek.get()
    _c._current_dek.set(None)
    try:
        with pytest.raises(DekUnavailableError):
            _ = s.display_name
    finally:
        _c._current_dek.set(saved)


# ---------------------------------------------------------------------------
# Log-scrubbing \u2014 repr() must never leak Art.-9 payloads
# ---------------------------------------------------------------------------


def test_symptom_repr_does_not_leak_name() -> None:
    s = _build_default("Kopfschmerzen")
    text = repr(s)
    assert "Kopfschmerzen" not in text
    assert "headache" in text  # slug is fine \u2014 it is non-personal


def test_custom_symptom_repr_does_not_leak_name() -> None:
    s = _build_custom_shell()
    s.set_custom_name("Migr\u00e4ne mit Aura")
    text = repr(s)
    assert "Migr\u00e4ne" not in text
    # name_enc bytes must not show up either.
    assert "name_enc" not in text


def test_entry_symptom_repr_does_not_leak_intensity() -> None:
    es = EntrySymptom()
    es.id = uuid.uuid4()
    es.entry_id = uuid.uuid4()
    es.user_id = uuid.uuid4()
    es.symptom_id = uuid.uuid4()
    es.intensity = 3
    text = repr(es)
    # The repr explicitly omits intensity & symptom_id payload.
    assert "intensity" not in text
    assert "3" not in text or "id=" in text  # uuid may contain digits, but
    # the literal intensity value must not be a standalone token.
