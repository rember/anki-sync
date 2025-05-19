from typing import Callable, Union, Literal, TypedDict

from aqt.main import AnkiQt
from aqt.errors import show_exception
from aqt.operations import QueryOp
from aqt.utils import openLink, showInfo
from aqt.profiles import ProfileManager

from . import auth_client, auth_server_loopback, auth_tokens

#:


class StateLoggedOut(TypedDict):
    _tag: Literal["LoggedOut"]


class StateSigningIn(TypedDict):
    _tag: Literal["SigningIn"]
    server_loopback: auth_server_loopback.ServerLoopback
    challenge: auth_client.Challenge


class StateSignedIn(TypedDict):
    _tag: Literal["SignedIn"]


StateAuth = Union[StateLoggedOut, StateSigningIn, StateSignedIn]


class SuccessOpSignIn(TypedDict):
    _tag: Literal["Success",]
    tokens: auth_tokens.Tokens


ErrorSignIn = Union[
    auth_client.ErrorClientAuth,
    auth_server_loopback.ErrorServerLoopback,
]

ResultSignIn = Union[SuccessOpSignIn, ErrorSignIn]


class Auth:
    _state: StateAuth

    def __init__(
        self,
        mw: AnkiQt,
        pm: ProfileManager,
        callback_state_auth: Callable[[StateAuth], None],
    ):
        self._mw = mw
        self._pm = pm
        self._callback_state_auth = callback_state_auth

        tokens = auth_tokens.get_tokens(mw.pm)
        if tokens is None:
            self._state = StateLoggedOut(_tag="LoggedOut")
            callback_state_auth(self._state)
        else:
            self._state = StateSignedIn(_tag="SignedIn")
            callback_state_auth(self._state)

    def _set_state(self, state: StateAuth):
        self._state = state
        self._callback_state_auth(self._state)

    def _sign_in_op(self):
        if self._state["_tag"] != "SigningIn":
            raise RuntimeError(f"Invalid state: {self._state['_tag']}")
        server_loopback = self._state["server_loopback"]
        challenge = self._state["challenge"]

        result_listen = server_loopback.listen()
        if result_listen["_tag"] == "ErrorServerLoopback":
            return result_listen
        if result_listen["data_auth"]["state"] != challenge["state"]:
            return auth_client.ErrorClientAuth(
                _tag="ErrorClientAuth", message="Invalid 'state' parameter."
            )

        result_exchange = auth_client.exchange(
            result_listen["data_auth"]["code"],
            server_loopback.uri_redirect,
            challenge["verifier"],
        )
        if result_exchange["_tag"] == "ErrorClientAuth":
            return result_exchange

        return SuccessOpSignIn(_tag="Success", tokens=result_exchange["tokens"])

    def _sign_in_failure(self, error: Union[Exception, ErrorSignIn]):
        if self._state["_tag"] != "SigningIn":
            raise RuntimeError(f"Invalid state: {self._state['_tag']}")
        server_loopback = self._state["server_loopback"]

        server_loopback.close()

        auth_tokens.set_tokens(self._pm, None)

        if isinstance(error, Exception):
            show_exception(parent=self._mw, exception=error)
        else:
            show_exception(
                parent=self._mw,
                exception=Exception(f'{error["_tag"]}: {error["message"]}'),
            )

        self._set_state(
            StateLoggedOut(
                _tag="LoggedOut",
            )
        )

    def _sign_in_success(self, result_sign_in: ResultSignIn):
        if self._state["_tag"] != "SigningIn":
            raise RuntimeError(f"Invalid state: {self._state['_tag']}")
        server_loopback = self._state["server_loopback"]

        if (
            result_sign_in["_tag"] == "ErrorClientAuth"
            or result_sign_in["_tag"] == "ErrorServerLoopback"
        ):
            return self._sign_in_failure(error=result_sign_in)

        server_loopback.close()

        auth_tokens.set_tokens(self._pm, result_sign_in["tokens"])
        showInfo("Signed in to Rember successfully.")

        self._set_state(
            StateSignedIn(
                _tag="SignedIn",
            )
        )

    def sign_in(self):
        if self._state["_tag"] != "LoggedOut":
            raise RuntimeError(f"Invalid state: {self._state['_tag']}")

        # Create server to receive the OAuth redirect
        server_loopback = auth_server_loopback.ServerLoopback()

        # Obtain URL for OAuth flow
        result_auth = auth_client.authorize(server_loopback.uri_redirect)

        # Open URL for OAuth flow in the user's browser
        openLink(result_auth["url"])
        showInfo("Please complete the Rember login process in your web browser.")

        self._set_state(
            StateSigningIn(
                _tag="SigningIn",
                server_loopback=server_loopback,
                challenge=result_auth["challenge"],
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

    def cancel_sign_in(self):
        if self._state["_tag"] != "SigningIn":
            raise RuntimeError(f"Invalid state: {self._state['_tag']}")
        server_loopback = self._state["server_loopback"]

        server_loopback.close()

        # Note that we don't set the state to LoggedOut here, since closing the
        # server will trigger `self._sign_in_failure`.

    def log_out(self):
        if self._state["_tag"] != "SignedIn":
            raise RuntimeError(f"Invalid state: {self._state['_tag']}")

        auth_tokens.set_tokens(self._pm, None)
        showInfo("Logged out from your Rember account")

        self._set_state(
            StateLoggedOut(
                _tag="LoggedOut",
            )
        )

    def act_based_on_state(self) -> None:
        if self._state["_tag"] == "LoggedOut":
            return self.sign_in()
        if self._state["_tag"] == "SigningIn":
            return self.cancel_sign_in()
        if self._state["_tag"] == "SignedIn":
            return self.log_out()

    def close(self) -> None:
        if self._state["_tag"] == "SigningIn":
            self._state["server_loopback"].close()
