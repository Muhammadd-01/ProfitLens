from __future__ import annotations

import pytest
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_password_hashing_and_verification():
    """Verify bcrypt hashes passwords with salt and verifies matches correctly."""
    pwd = "MySecretSecurePassword123!"
    hashed = hash_password(pwd)

    # Hash should not be equal to plain text
    assert hashed != pwd
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    # Correct password verifies
    assert verify_password(pwd, hashed) is True

    # Incorrect password fails
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_creation_and_decoding():
    """Verify JWT token contains user_id and org_id and decodes successfully."""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    org_id = "987fcdeb-51a2-43f7-9012-345678901234"

    token = create_access_token(user_id=user_id, organization_id=org_id)
    assert isinstance(token, str)
    assert len(token) > 20

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded.user_id == user_id
    assert decoded.organization_id == org_id


def test_jwt_token_invalid_tampered():
    """Verify tampered JWT token is rejected."""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    org_id = "987fcdeb-51a2-43f7-9012-345678901234"

    token = create_access_token(user_id=user_id, organization_id=org_id)
    tampered = token[:-4] + "abcd"

    assert decode_access_token(tampered) is None
