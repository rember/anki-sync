import os
from typing import Literal, TypedDict, Union

import requests

from . import info

#: Shared

URL_BASE = f"https://www.{info.SITE_REMBER}"
ENDPOINT_REPLICACHE_PULL_FOR_ANKI = f"{URL_BASE}/api/v1/replicache-pull-for-anki"
VERSION_SCHEMA_REPLICACHE = "7"


class ErrorClientPuller:
    def __init__(self, message: str):
        self._tag: Literal["ErrorClientRember"] = "ErrorClientRember"
        self.message = message


#: replicache_pull_for_anki


class PutOperation(TypedDict):
    op: Literal["put"]
    key: str
    value: dict


class DelOperation(TypedDict):
    op: Literal["del"]
    key: str


class ClearOperation(TypedDict):
    op: Literal["clear"]


Patch = list[Union[PutOperation, DelOperation, ClearOperation]]


class SuccessReplicachePullForAnki:
    def __init__(self, cookie: Union[int, None], patch: Patch):
        self._tag: Literal["Success"] = "Success"
        self.cookie = cookie
        self.patch = patch


ResultReplicachePullForAnki = Union[SuccessReplicachePullForAnki, ErrorClientPuller]


def replicache_pull_for_anki(
    cookie_replicache: Union[int, None], token_access: str
) -> ResultReplicachePullForAnki:
    payload = {
        "version": "1",
        "versionAddonRemberAnkiSync": info.VERSION_REMBER_ANKI_SYNC,
        "versionSchema": VERSION_SCHEMA_REPLICACHE,
        "cookie": cookie_replicache,
    }
    headers = {"authorization": f"Bearer {token_access}"}

    response = requests.post(
        ENDPOINT_REPLICACHE_PULL_FOR_ANKI, json=payload, headers=headers
    )

    if response.ok:
        try:
            data = response.json()
            return _decode_response_replicache_pull_for_anki(data)
        except Exception as e:
            return ErrorClientPuller(message=f"Invalid response: {str(e)}")
    else:
        # Intercept `Replicache/ErrorVersionNotSupported`
        try:
            data = response.json()
            if data.get("_tag") == "Replicache/ErrorVersionNotSupported":
                return ErrorClientPuller(message="Please update the Rember addon")
        except:
            return ErrorClientPuller(
                message=f"Request failed with status {response.status_code}: {response.text}"
            )
        return ErrorClientPuller(
            message=f"Request failed with status {response.status_code}: {response.text}"
        )


def _decode_patch(data: list) -> Patch:
    result: Patch = []

    for operation in data:
        if not isinstance(operation, dict):
            raise ValueError("Each operation must be a dictionary")

        op = operation.get("op")
        if not isinstance(op, str):
            raise ValueError("Operation must have a string 'op' field")

        if op == "put":
            if "key" not in operation or "value" not in operation:
                raise ValueError("Put operation must have 'key' and 'value' fields")
            if not isinstance(operation["key"], str):
                raise ValueError("Put operation key must be a string")
            if not isinstance(operation["value"], dict):
                raise ValueError("Put operation value must be a dictionary")
            result.append(
                {"op": "put", "key": operation["key"], "value": operation["value"]}
            )

        elif op == "del":
            if "key" not in operation:
                raise ValueError("Del operation must have a 'key' field")
            if not isinstance(operation["key"], str):
                raise ValueError("Del operation key must be a string")
            result.append({"op": "del", "key": operation["key"]})

        elif op == "clear":
            result.append({"op": "clear"})

        else:
            raise ValueError(f"Invalid operation type: {op}")

    return result


def _decode_response_replicache_pull_for_anki(
    data: dict,
) -> SuccessReplicachePullForAnki:
    if "cookie" not in data:
        raise ValueError("Response must contain 'cookie' field")

    if "patch" not in data:
        raise ValueError("Response must contain 'patch' field")

    cookie = data["cookie"]
    if cookie is not None and not isinstance(cookie, int):
        raise ValueError("Cookie must be an integer or None")

    if not isinstance(data["patch"], list):
        raise ValueError("Patch must be a list")
    patch = _decode_patch(data["patch"])

    return SuccessReplicachePullForAnki(cookie=cookie, patch=patch)
