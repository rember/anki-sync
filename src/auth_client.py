import base64
import hashlib
import json
import secrets
import time
import urllib.parse
from typing import Optional, TypedDict, Union

import requests

from . import auth_tokens

#: Shared

ISSUER_URL = "https://auth.development.rember.com"
ENDPOINT_AUTHORIZATION = f"{ISSUER_URL}/authorize"
ENDPOINT_TOKEN = f"{ISSUER_URL}/token"
ID_CLIENT = "rember-anki-sync"


class ErrorOAuth(TypedDict):
    tag: str
    message: str


#: Utils


def _generate_verifier(length_bytes: int = 64) -> str:
    """Generates a high-entropy cryptographic random string used as a PKCE code verifier.
    Uses `length_bytes` random bytes, resulting in a base64url encoded string of length ~4/3 * length_bytes.
    RFC 7636 specifies verifier length between 43 and 128 characters.
    64 bytes -> ~86 characters, which is well within the spec.
    """
    return secrets.token_urlsafe(length_bytes)


def _generate_challenge(code_verifier: str) -> str:
    """Generates a PKCE code challenge from a code verifier (S256 method)."""
    sha256_hash = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    challenge_value = (
        base64.urlsafe_b64encode(sha256_hash).decode("utf-8").replace("=", "")
    )
    return challenge_value


def _generate_random_state(length_bytes: int = 32) -> str:
    """Generates a cryptographically secure random string for the state parameter."""
    return secrets.token_urlsafe(length_bytes)


#: Authorize


class Challenge(TypedDict):
    state: str
    verifier: str


class ResultAuthorize(TypedDict):
    url: str
    challenge: Challenge


def authorize(redirect_uri: str) -> ResultAuthorize:
    """
    Constructs the authorization URL for the OAuth 2.0 flow with PKCE.

    Args:
        redirect_uri: The URI to which the user will be redirected after authorization.

    Returns:
        An ResultAuthorize dictionary containing the authorization URL and the challenge object
        (with state and verifier).
    """
    verifier = _generate_verifier()
    code_challenge = _generate_challenge(verifier)
    state = _generate_random_state()

    params = {
        "client_id": ID_CLIENT,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
    }
    # Using urllib.parse.urlencode ensures proper encoding of parameters
    query_string = urllib.parse.urlencode(params)
    url_authorization = f"{ENDPOINT_AUTHORIZATION}?{query_string}"

    return {
        "url": url_authorization,
        "challenge": {"state": state, "verifier": verifier},
    }


#: Exchange

ResultExchange = Union[auth_tokens.Tokens, ErrorOAuth]


def exchange(code: str, redirect_uri: str, verifier: str) -> ResultExchange:
    """
    Exchanges an authorization code for access and refresh tokens.

    Args:
        code: The authorization code received from the OAuth server.
        redirect_uri: The redirect URI used in the initial authorization request.
        verifier: The PKCE code verifier (referred to as code_verifier in the OAuth spec for the request body by the user, but key in payload is 'verifier').

    Returns:
        Tokens if successful, ErrorOAuth otherwise.
    """
    payload = {
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "client_id": ID_CLIENT,
        "code_verifier": verifier,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(ENDPOINT_TOKEN, data=payload, headers=headers)

    if response.ok:
        data = response.json()
        return auth_tokens.Tokens(
            access=data["access_token"],
            refresh=data["refresh_token"],
        )
    else:
        return ErrorOAuth(
            tag="invalid_authorization_code",
            message="Invalid authorization code.",
        )


#: Refresh

ResultRefresh = Union[None, auth_tokens.Tokens, ErrorOAuth]


def refresh(token_refresh: str, token_access: Optional[str] = None) -> ResultRefresh:
    """
    Refreshes access and refresh tokens using a refresh token.
    Optionally checks if the current access token is still valid before making a request.

    Args:
        token_refresh: The refresh token.
        token_access: Optional. The current access token to check for expiration.

    Returns:
        Tokens if successfully refresh, None if the access token has not expired, ErrorOAuth otherwise.
    """
    if token_access:
        try:
            jwt_b64 = token_access.split(".")[1]
            jwt_b64 += "=" * (-len(jwt_b64) % 4)
            jwt_decoded = base64.urlsafe_b64decode(jwt_b64).decode("utf-8")
            jwt_json = json.loads(jwt_decoded)
            exp = jwt_json.get("exp")

            if isinstance(exp, (int, float)):
                # Allow 30s window for expiration
                if exp > time.time() + 30:
                    return None
        except Exception:
            return ErrorOAuth(
                tag="invalid_token_access",
                message="Invalid access token.",
            )

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": token_refresh,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(ENDPOINT_TOKEN, data=payload, headers=headers)

    if response.ok:
        data = response.json()
        return auth_tokens.Tokens(
            access=data["access_token"],
            refresh=data["refresh_token"],
        )
    else:
        return ErrorOAuth(
            tag="invalid_refresh_token",
            message="Invalid refresh token.",
        )
