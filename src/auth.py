from typing import TypedDict, Optional

from aqt.profiles import ProfileManager

#: Tokens
# Store the tokens in the user profile, like for the native AnkiHub integration
# in Anki. The user profile is serialized as a Pickle file, a schema is not
# enforced.
# REFS: https://github.com/ankitects/anki/blob/d3d6bd8/qt/aqt/profiles.py#L736-L740


class RemberTokens(TypedDict):
    access: str
    refresh: str


def set_rember_tokens(pm: ProfileManager, tokens: Optional[RemberTokens]) -> None:
    assert pm.profile is not None
    if tokens:
        pm.profile["thirdPartyRemberTokenAccess"] = tokens["access"]
        pm.profile["thirdPartyRemberTokenRefresh"] = tokens["refresh"]
    else:
        pm.profile["thirdPartyRemberTokenAccess"] = None
        pm.profile["thirdPartyRemberTokenRefresh"] = None


def rember_tokens(pm: ProfileManager) -> Optional[RemberTokens]:
    assert pm.profile is not None
    token_access = pm.profile.get("thirdPartyRemberTokenAccess")
    token_refresh = pm.profile.get("thirdPartyRemberTokenRefresh")

    if token_access is None or token_refresh is None:
        return None

    return {"access": token_access, "refresh": token_refresh}
