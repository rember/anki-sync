from typing import Callable, Union, Literal, TypedDict, Protocol, Any

from aqt.main import AnkiQt
from aqt.errors import show_exception
from aqt.operations import QueryOp
from aqt.utils import openLink, showInfo
from aqt.profiles import ProfileManager

from . import auth_client, auth_server_loopback, auth_tokens

#: Types


class StateUnknown:
    def __init__(self):
        self._tag: Literal["Unknown"] = "Unknown"


class StateLoggedOut:
    def __init__(self):
        self._tag: Literal["LoggedOut"] = "LoggedOut"


class StateSigningIn:
    def __init__(
        self,
        server_loopback: auth_server_loopback.ServerLoopback,
        challenge: auth_client.Challenge,
    ):
        self._tag: Literal["SigningIn"] = "SigningIn"
        self.server_loopback = server_loopback
        self.challenge = challenge


class StateSignedIn:
    def __init__(
        self,
        tokens: auth_tokens.Tokens,
    ):
        self._tag: Literal["SignedIn"] = "SignedIn"
        self.tokens = tokens


StateAuth = Union[StateUnknown, StateLoggedOut, StateSigningIn, StateSignedIn]


class SuccessSignIn:
    def __init__(self, tokens: auth_tokens.Tokens):
        self._tag: Literal["Success"] = "Success"
        self.tokens = tokens


ErrorSignIn = Union[
    auth_client.ErrorClientAuth,
    auth_server_loopback.ErrorServerLoopback,
]

ResultSignIn = Union[SuccessSignIn, ErrorSignIn]

#:


class Auth:
    state: StateAuth

    ##: __init__

    def __init__(
        self,
        mw: AnkiQt,
        callback_state_auth: Callable[[StateAuth], None],
    ):
        self._mw = mw
        self._callback_state_auth = callback_state_auth

        self.state = StateUnknown()
        self._callback_state_auth(self.state)

    ##: _set_state

    def _set_state(self, state: StateAuth):
        self.state = state
        self._callback_state_auth(self.state)

    ##: close

    def close(self) -> None:
        if self.state._tag == "SigningIn":
            self.state.server_loopback.close()

        self._set_state(StateUnknown())

    ##: refresh_state_from_tokens

    def refresh_state_from_tokens(self):
        tokens = auth_tokens.get_tokens(self._mw.pm)

        if tokens is None and self.state._tag != "LoggedOut":
            self._set_state(StateLoggedOut())
            return

        if tokens is not None and self.state._tag != "SignedIn":
            self._set_state(StateSignedIn(tokens))
            return

    ##: sign_in

    def _sign_in_op(self):
        if self.state._tag != "SigningIn":
            raise RuntimeError(f"Invalid state: {self.state._tag}")
        server_loopback = self.state.server_loopback
        challenge = self.state.challenge

        result_listen = server_loopback.listen()
        if result_listen._tag == "ErrorServerLoopback":
            return result_listen
        if result_listen.data_auth.state != challenge.state:
            return auth_client.ErrorClientAuth(message="Invalid 'state' parameter.")

        result_exchange = auth_client.exchange(
            result_listen.data_auth.code,
            server_loopback.uri_redirect,
            challenge.verifier,
        )
        if result_exchange._tag == "ErrorClientAuth":
            return result_exchange

        return SuccessSignIn(tokens=result_exchange.tokens)

    def _sign_in_failure(self, error: Union[Exception, ErrorSignIn]):
        if self.state._tag != "SigningIn":
            raise RuntimeError(f"Invalid state: {self.state._tag}")
        server_loopback = self.state.server_loopback

        server_loopback.close()

        auth_tokens.set_tokens(self._mw.pm, None)
        self._set_state(StateLoggedOut())

        if isinstance(error, Exception):
            show_exception(parent=self._mw, exception=error)
        else:
            show_exception(
                parent=self._mw,
                exception=Exception(f"{error._tag}: {error.message}"),
            )

    def _sign_in_success(self, result_sign_in: ResultSignIn):
        if self.state._tag != "SigningIn":
            raise RuntimeError(f"Invalid state: {self.state._tag}")
        server_loopback = self.state.server_loopback

        if result_sign_in._tag != "Success":
            return self._sign_in_failure(error=result_sign_in)

        server_loopback.close()

        auth_tokens.set_tokens(self._mw.pm, result_sign_in.tokens)
        showInfo("Signed in to Rember successfully.")

        self._set_state(StateSignedIn(result_sign_in.tokens))

    def sign_in(self):
        if self.state._tag != "LoggedOut":
            raise RuntimeError(f"Invalid state: {self.state._tag}")

        # Create server to receive the OAuth redirect
        server_loopback = auth_server_loopback.ServerLoopback()

        # Obtain URL for OAuth flow
        result_auth = auth_client.authorize(server_loopback.uri_redirect)

        # Open URL for OAuth flow in the user's browser
        openLink(result_auth.url)
        showInfo("Please complete the Rember login process in your web browser.")

        self._set_state(
            StateSigningIn(
                server_loopback=server_loopback,
                challenge=result_auth.challenge,
            )
        )

        # Wait for the OAuth callback in the background
        QueryOp(
            parent=self._mw,
            op=lambda _: self._sign_in_op(),
            success=lambda result_sign_in: self._sign_in_success(result_sign_in),
        ).failure(
            lambda error: self._sign_in_failure(error),
        ).without_collection().run_in_background()

    ##: cancel_sign_in

    def cancel_sign_in(self):
        if self.state._tag != "SigningIn":
            raise RuntimeError(f"Invalid state: {self.state._tag}")
        server_loopback = self.state.server_loopback

        server_loopback.close()

        # Note that we don't set the state to LoggedOut here, since closing the
        # server will trigger `self._sign_in_failure`.

    ##: log_out

    def log_out(self):
        if self.state._tag != "SignedIn":
            raise RuntimeError(f"Invalid state: {self.state._tag}")

        auth_tokens.set_tokens(self._mw.pm, None)
        showInfo("Logged out from your Rember account")

        self._set_state(StateLoggedOut())

    ##: refresh_token

    def _refresh_token_op(self):
        if self.state._tag != "SignedIn":
            raise RuntimeError(f"Invalid state: {self.state._tag}")
        tokens = self.state.tokens

        return auth_client.refresh(
            token_refresh=tokens.refresh, token_access=tokens.access
        )

    def _refresh_token_failure(self, error: Union[Exception, auth_client.ErrorRefresh]):
        if self.state._tag != "SignedIn":
            raise RuntimeError(f"Invalid state: {self.state._tag}")

        auth_tokens.set_tokens(self._mw.pm, None)
        self._set_state(StateLoggedOut())

        if isinstance(error, Exception):
            show_exception(parent=self._mw, exception=error)
        else:
            show_exception(
                parent=self._mw,
                exception=Exception(f"{error._tag}: {error.message}"),
            )

    def _refresh_token_success(self, result_refresh: auth_client.ResultRefresh):
        if self.state._tag != "SignedIn":
            raise RuntimeError(f"Invalid state: {self.state._tag}")

        if result_refresh._tag != "Success":
            return self._refresh_token_failure(error=result_refresh)

        if result_refresh.tokens is not None:
            auth_tokens.set_tokens(self._mw.pm, result_refresh.tokens)
            self._set_state(StateSignedIn(result_refresh.tokens))

    def refresh_token(self):
        if self.state._tag != "SignedIn":
            raise RuntimeError(f"Invalid state: {self.state._tag}")

        # Refresh the auth tokens in the background
        QueryOp(
            parent=self._mw,
            op=lambda _: self._refresh_token_op(),
            success=lambda result_refresh: self._refresh_token_success(result_refresh),
        ).failure(
            lambda error: self._sign_in_failure(error),
        ).without_collection().run_in_background()
