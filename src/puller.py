from typing import Union

from aqt.errors import show_exception
from aqt.main import AnkiQt
from aqt.operations import QueryOp

from . import auth, auth_client, auth_tokens, puller_client, rembs, user_files, users

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
        if self._mw.col is None:
            raise RuntimeError("Collection is None")
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
        result_replicache_pull_for_anki = puller_client.replicache_pull_for_anki(
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
        _users = users.Users(user_files=self._user_files)
        _users.process_patch(patch)
        _rembs = rembs.Rembs(col=self._mw.col)
        _rembs.process_patch(patch)

        return result_replicache_pull_for_anki

    def _pull_failure(
        self,
        error: Union[
            Exception,
            puller_client.ErrorClientPuller,
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
            puller_client.ResultReplicachePullForAnki,
            auth_client.ErrorClientAuth,
            auth_tokens.ErrorTokens,
        ],
    ):
        if self._auth.state._tag != "SignedIn":
            raise RuntimeError(f"Invalid auth state: {self._auth.state._tag}")

        if result_replicache_pull_for_anki._tag != "Success":
            return self._pull_failure(error=result_replicache_pull_for_anki)

        # # TODO:
        # print(f"Cookie: {result_replicache_pull_for_anki.cookie}")
        # print(f"Patch: {json.dumps(result_replicache_pull_for_anki.patch, indent=2)}")

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
