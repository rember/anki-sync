from typing import Union

from aqt.errors import show_exception
from aqt.main import AnkiQt
from aqt.operations import QueryOp

from . import (
    auth,
    auth_client,
    auth_tokens,
    decks,
    logger,
    models,
    notes,
    puller_client,
    puller_cookie_replicache,
    user_files,
    users,
)

#:


class Puller:
    ##: __init__

    def __init__(
        self,
        mw: AnkiQt,
        auth: auth.Auth,
        user_files: user_files.UserFiles,
        logger: logger.Logger,
    ):
        self._mw = mw
        self._auth = auth
        self._user_files = user_files
        self._cookies_replicache = puller_cookie_replicache.CookieReplicache(
            user_files=self._user_files
        )
        self._logger = logger

    ##: pull

    def _pull_op(
        self,
    ) -> Union[
        puller_client.SuccessReplicachePullForAnki,
        puller_client.ErrorClientPuller,
        auth_client.ErrorClientAuth,
        auth_tokens.ErrorTokens,
    ]:
        if self._auth.state._tag != "SignedIn":
            raise RuntimeError(f"Invalid auth state: {self._auth.state._tag}")
        if self._mw.col is None:
            raise RuntimeError("Collection is None")
        tokens = self._auth.state.tokens

        self._logger.info("Pull started", self._mw)

        # Refresh the auth tokens
        result_refresh = self._auth.refresh_tokens()
        if result_refresh._tag != "Success":
            return result_refresh
        if result_refresh.tokens is not None:
            tokens = result_refresh.tokens

        # Get the stored cookie or None if not found
        cookie_replicache = self._cookies_replicache.get()

        # Pull
        result_replicache_pull_for_anki = puller_client.replicache_pull_for_anki(
            cookie_replicache=cookie_replicache, token_access=tokens.access
        )
        if result_replicache_pull_for_anki._tag != "Success":
            return result_replicache_pull_for_anki

        # Store the new cookie for future pulls if successful
        self._cookies_replicache.set(result_replicache_pull_for_anki.cookie)

        # Process patch
        patch = result_replicache_pull_for_anki.patch
        _users = users.Users(user_files=self._user_files)
        _models = models.Models(col=self._mw.col)
        _decks = decks.Decks(col=self._mw.col)
        _notes = notes.Notes(col=self._mw.col, models=_models, decks=_decks)
        _users.process_patch(patch)
        self._logger.info("Users patch processed successfully", self._mw)
        _notes.process_patch(patch)
        self._logger.info("Notes patch processed successfully", self._mw)

        return result_replicache_pull_for_anki

    def _pull_failure(
        self,
        error: Union[
            Exception,
            puller_client.ErrorClientPuller,
            auth_client.ErrorClientAuth,
            auth_tokens.ErrorTokens,
        ],
    ) -> None:
        if self._auth.state._tag != "SignedIn":
            raise RuntimeError(f"Invalid auth state: {self._auth.state._tag}")

        if isinstance(error, Exception):
            self._logger.error(f"Pull failed.", self._mw, exception=error)
            show_exception(parent=self._mw, exception=error)
        else:
            self._logger.error(
                f"Pull failed. {error._tag}: {error.message}",
                self._mw,
            )
            show_exception(
                parent=self._mw,
                exception=RuntimeError(f"Pull failed. {error._tag}: {error.message}"),
            )

    def _pull_success(
        self,
        result_replicache_pull_for_anki: Union[
            puller_client.ResultReplicachePullForAnki,
            auth_client.ErrorClientAuth,
            auth_tokens.ErrorTokens,
        ],
    ) -> None:
        if self._auth.state._tag != "SignedIn":
            raise RuntimeError(f"Invalid auth state: {self._auth.state._tag}")

        if result_replicache_pull_for_anki._tag != "Success":
            return self._pull_failure(error=result_replicache_pull_for_anki)

        self._logger.info("Pull succeeded", self._mw)

    def pull(self) -> None:
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
