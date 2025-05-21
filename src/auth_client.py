import base64
import hashlib
import secrets
import time
import urllib.parse
from typing import Literal, Optional, TypedDict, Union

import requests

from . import auth_tokens

#: Shared

ISSUER_URL = "https://auth.development.rember.com"
ENDPOINT_AUTHORIZATION = f"{ISSUER_URL}/authorize"
ENDPOINT_TOKEN = f"{ISSUER_URL}/token"
ID_CLIENT = "rember-anki-sync"


class ErrorClientAuth:
    def __init__(self, message: str):
        self._tag: Literal["ErrorClientAuth"] = "ErrorClientAuth"
        self.message = message


#: Utils


def _generate_verifier(length_bytes: int = 64) -> str:
    """
    Generates a high-entropy cryptographic random string used as a PKCE code verifier.
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


#: authorize


class Challenge:
    def __init__(self, state: str, verifier: str):
        self.state = state
        self.verifier = verifier


class ResultAuthorize:
    def __init__(self, url: str, challenge: Challenge):
        self.url = url
        self.challenge = challenge


def authorize(redirect_uri: str) -> ResultAuthorize:
    """Constructs the authorization URL for the OAuth 2.0 flow with PKCE."""
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

    return ResultAuthorize(
        url=url_authorization,
        challenge=Challenge(state=state, verifier=verifier),
    )


#: exchange


class SuccessExchange:
    def __init__(self, tokens: auth_tokens.Tokens):
        self._tag: Literal["Success"] = "Success"
        self.tokens = tokens


ResultExchange = Union[SuccessExchange, ErrorClientAuth]


def exchange(code: str, redirect_uri: str, verifier: str) -> ResultExchange:
    """Exchanges an authorization code for access and refresh tokens."""
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
        return SuccessExchange(
            tokens=auth_tokens.Tokens(
                access=data["access_token"],
                refresh=data["refresh_token"],
            )
        )
    else:
        return ErrorClientAuth(message="Invalid authorization code.")


#: refresh


class SuccessRefresh:
    def __init__(self, tokens: Union[auth_tokens.Tokens, None]):
        self._tag: Literal["Success"] = "Success"
        self.tokens = tokens


ErrorRefresh = Union[ErrorClientAuth, auth_tokens.ErrorTokens]


ResultRefresh = Union[SuccessRefresh, ErrorRefresh]


def refresh(token_refresh: str, token_access: Optional[str] = None) -> ResultRefresh:
    """
    Refreshes access and refresh tokens using a refresh token.
    Optionally checks if the current access token is still valid before making a request.
    """
    if token_access:
        result_decode_token_access = auth_tokens.decode_token_access(token_access)
        if result_decode_token_access._tag == "ErrorTokens":
            return result_decode_token_access
        # Allow 30s window for expiration
        if result_decode_token_access.payload.exp > time.time() + 30:
            return SuccessRefresh(tokens=None)

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": token_refresh,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(ENDPOINT_TOKEN, data=payload, headers=headers)

    if response.ok:
        data = response.json()
        return SuccessRefresh(
            tokens=auth_tokens.Tokens(
                access=data["access_token"],
                refresh=data["refresh_token"],
            )
        )
    else:
        return ErrorClientAuth(message="Invalid refresh token.")
