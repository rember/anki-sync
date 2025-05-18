# Store the tokens in the user profile, like for the native AnkiHub integration
# in Anki. The user profile is serialized as a Pickle file, a schema is not
# enforced.
# REFS: https://github.com/ankitects/anki/blob/d3d6bd8/qt/aqt/profiles.py#L736-L740

import base64
import json
from typing import Literal, Optional, TypedDict, Union

from aqt.profiles import ProfileManager

#:


class Tokens(TypedDict):
    access: str
    refresh: str


class PayloadTokenAccess(TypedDict):
    exp: int  # Expiration time (Unix timestamp)


class ErrorTokens(TypedDict):
    _tag: Literal["ErrorTokens"]
    message: str


def set_tokens(pm: ProfileManager, tokens: Optional[Tokens]) -> None:
    assert pm.profile is not None
    if tokens:
        pm.profile["thirdPartyRemberTokenAccess"] = tokens["access"]
        pm.profile["thirdPartyRemberTokenRefresh"] = tokens["refresh"]
    else:
        pm.profile["thirdPartyRemberTokenAccess"] = None
        pm.profile["thirdPartyRemberTokenRefresh"] = None


def get_tokens(pm: ProfileManager) -> Optional[Tokens]:
    assert pm.profile is not None
    token_access = pm.profile.get("thirdPartyRemberTokenAccess")
    token_refresh = pm.profile.get("thirdPartyRemberTokenRefresh")

    if token_access is None or token_refresh is None:
        return None

    return {"access": token_access, "refresh": token_refresh}


class SuccessDecodeTokenAccess(TypedDict):
    _tag: Literal["Success"]
    payload: PayloadTokenAccess


ResultDecodeTokenAccess = Union[SuccessDecodeTokenAccess, ErrorTokens]


def decode_token_access(token_access: str) -> ResultDecodeTokenAccess:
    try:
        jwt_b64 = token_access.split(".")[1]
        jwt_b64 += "=" * (-len(jwt_b64) % 4)
        jwt_decoded = base64.urlsafe_b64decode(jwt_b64).decode("utf-8")
        jwt_json = json.loads(jwt_decoded)

        if not isinstance(jwt_json.get("exp"), (int, float)):
            raise ValueError("Invalid 'exp' field")

        if not isinstance(jwt_json.get("properties", {}).get("idUser"), str):
            raise ValueError("Invalid 'properties.idUser' field")

        return SuccessDecodeTokenAccess(
            _tag="Success", payload=PayloadTokenAccess(exp=int(jwt_json["exp"]))
        )

    except:
        return ErrorTokens(_tag="ErrorTokens", message="Invalid access token.")
