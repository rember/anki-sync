import json
from typing import Union

from aqt.errors import show_exception
from aqt.main import AnkiQt
from aqt.operations import QueryOp

from . import auth, auth_client, auth_tokens, rember_client, user_files
from .puller_user import put_user, del_user, clear_users
from .puller_remb import put_remb, del_remb, clear_rembs

#:


class Puller:
    ##: __init__

    def __init__(self, mw: AnkiQt, auth: auth.Auth, user_files: user_files.UserFiles):
        self._mw = mw
        self._auth = auth
        self._user_files = user_files

    ##: pull

    def _pull_op(self):
        if self._auth.state._tag != "SignedIn":
            raise RuntimeError(f"Invalid auth state: {self._auth.state._tag}")
        tokens = self._auth.state.tokens

        # Refresh the auth tokens
        result_refresh = self._auth.refresh_tokens()
        if result_refresh._tag != "Success":
            return result_refresh
        if result_refresh.tokens is not None:
            tokens = result_refresh.tokens

        # Get the stored cookie or None if not found
        # TODO: cookie_replicache = self._user_files.get("cookie_replicache")
        cookie_replicache = None

        # Pull
        result_replicache_pull_for_anki = rember_client.replicache_pull_for_anki(
            cookie_replicache=cookie_replicache, token_access=tokens.access
        )
        if result_replicache_pull_for_anki._tag != "Success":
            return result_replicache_pull_for_anki

        # Store the new cookie for future pulls if successful
        self._user_files.set(
            "cookie_replicache", result_replicache_pull_for_anki.cookie
        )

        # Process patch
        patch = result_replicache_pull_for_anki.patch
        # Handle clear operation if it's the first operation
        if patch[0]["op"] == "clear":
            clear_users(self._user_files, patch)
            clear_rembs(self._user_files, patch)
            return result_replicache_pull_for_anki
        # Process other operations
        for op in patch:
            if op["op"] == "clear":
                raise RuntimeError(
                    "Clear operation must be the first operation in the patch"
                )
            if op["op"] == "put":
                if op["key"].startswith("User/"):
                    put_user(self._user_files, op["key"], op["value"])
                if op["key"].startswith("Remb/"):
                    put_remb(self._user_files, op["key"], op["value"])
            elif op["op"] == "del":
                if op["key"].startswith("User/"):
                    del_user(self._user_files, op["key"])
                if op["key"].startswith("Remb/"):
                    del_remb(self._user_files, op["key"])

        return result_replicache_pull_for_anki

    def _pull_failure(
        self,
        error: Union[
            Exception,
            rember_client.ErrorClientRember,
            auth_client.ErrorClientAuth,
            auth_tokens.ErrorTokens,
        ],
    ):
        if self._auth.state._tag != "SignedIn":
            raise RuntimeError(f"Invalid auth state: {self._auth.state._tag}")

        print(error)
        if isinstance(error, Exception):
            show_exception(parent=self._mw, exception=error)
        else:
            show_exception(
                parent=self._mw,
                exception=Exception(f"{error._tag}: {error.message}"),
            )

    def _pull_success(
        self,
        result_replicache_pull_for_anki: Union[
            rember_client.ResultReplicachePullForAnki,
            auth_client.ErrorClientAuth,
            auth_tokens.ErrorTokens,
        ],
    ):
        if self._auth.state._tag != "SignedIn":
            raise RuntimeError(f"Invalid auth state: {self._auth.state._tag}")

        if result_replicache_pull_for_anki._tag != "Success":
            return self._pull_failure(error=result_replicache_pull_for_anki)

        # TODO:
        print(f"Cookie: {result_replicache_pull_for_anki.cookie}")
        print(f"Patch: {json.dumps(result_replicache_pull_for_anki.patch, indent=2)}")

    def pull(self):
        if self._auth.state._tag != "SignedIn":
            return

        # Pull in the background
        QueryOp(
            parent=self._mw,
            op=lambda _: self._pull_op(),
            success=lambda result_pull: self._pull_success(result_pull),
        ).failure(
            lambda error: self._pull_failure(error),
        ).with_progress(
            "Syncing Rember data..."
        ).run_in_background()
