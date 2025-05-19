from aqt import appVersion

required_anki_version = (23, 10, 0)
anki_version = tuple(int(segment) for segment in appVersion.split("."))
if anki_version < required_anki_version:
    raise Exception(
        f"Minimum Anki version supported: {required_anki_version[0]}.{required_anki_version[1]}.{required_anki_version[2]}"
    )

from typing import Literal, TypedDict, Union

from aqt import gui_hooks, mw
from aqt.errors import show_exception
from aqt.operations import QueryOp
from aqt.qt import QAction, qconnect
from aqt.utils import openLink, showInfo

from . import auth_client, auth_server_loopback, auth_tokens

#: "Sign in"/"Log out" menu item


class SuccessOpSignIn(TypedDict):
    _tag: Literal["Success",]
    tokens: auth_tokens.Tokens


ErrorSignIn = Union[
    auth_client.ErrorClientAuth,
    auth_server_loopback.ErrorServerLoopback,
]

ResultSignIn = Union[SuccessOpSignIn, ErrorSignIn]


def _op_sign_in(
    server_loopback: auth_server_loopback.ServerLoopback,
    challenge: auth_client.Challenge,
) -> ResultSignIn:
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


def _success_sign_in(
    server_loopback: auth_server_loopback.ServerLoopback, result_sign_in: ResultSignIn
) -> None:
    if (
        result_sign_in["_tag"] == "ErrorClientAuth"
        or result_sign_in["_tag"] == "ErrorServerLoopback"
    ):
        return _failure_sign_in(server_loopback=server_loopback, error=result_sign_in)

    server_loopback.close()

    if mw.pm is None:
        raise Exception("ProfileManager not defined")
    auth_tokens.set_tokens(mw.pm, result_sign_in["tokens"])

    refresh_action_sign_in()

    showInfo("Signed in to Rember successfully.")


def _failure_sign_in(
    server_loopback: auth_server_loopback.ServerLoopback,
    error: Union[Exception, ErrorSignIn],
) -> None:
    server_loopback.close()

    auth_tokens.set_tokens(mw.pm, None)

    refresh_action_sign_in()

    if isinstance(error, Exception):
        show_exception(parent=mw, exception=error)
    else:
        show_exception(
            parent=mw, exception=Exception(f'{error["_tag"]}: {error["message"]}')
        )


def on_sign_in() -> None:
    if mw.pm is None:
        raise Exception("ProfileManager not defined")

    # Create server to receive the OAuth redirect
    server_loopback = auth_server_loopback.ServerLoopback()

    # Obtain URL for OAuth flow
    result_auth = auth_client.authorize(server_loopback.uri_redirect)

    # Open URL for OAuth flow in the user's browser
    openLink(result_auth["url"])
    showInfo("Please complete the Rember login process in your web browser.")

    # Wait for the OAuth callback in the background
    QueryOp(
        parent=mw,
        op=lambda _: _op_sign_in(server_loopback, result_auth["challenge"]),
        success=lambda result_sign_in: _success_sign_in(
            server_loopback, result_sign_in
        ),
    ).failure(
        lambda error: _failure_sign_in(server_loopback, error),
    ).without_collection().run_in_background()


def on_log_out() -> None:
    if mw.pm is None:
        raise Exception("ProfileManager not defined")

    auth_tokens.set_tokens(mw.pm, None)
    showInfo("Logged out from your Rember account")

    refresh_action_sign_in()


def refresh_action_sign_in() -> None:
    if mw.pm is None:
        raise Exception("ProfileManager not defined")

    tokens = auth_tokens.get_tokens(mw.pm)

    if tokens is None:
        action_sign_in.setText("Sign in")
        try:
            action_sign_in.triggered.disconnect(on_log_out)
        except:
            pass  # No function is connected yet
        qconnect(action_sign_in.triggered, on_sign_in)
    else:
        action_sign_in.setText("Log out")
        try:
            action_sign_in.triggered.disconnect(on_sign_in)
        except:
            pass  # No function is connected yet
        qconnect(action_sign_in.triggered, on_log_out)


action_sign_in = QAction("Sign in")

gui_hooks.profile_did_open.append(refresh_action_sign_in)

#: "Status" menu item


def on_status() -> None:
    if mw.pm is None:
        raise Exception("ProfileManager not defined")

    tokens = auth_tokens.get_tokens(mw.pm)
    if tokens is None:
        showInfo("Logged out")
        return

    result_decode_token_access = auth_tokens.decode_token_access(tokens["access"])
    if result_decode_token_access["_tag"] == "ErrorTokens":
        showInfo("Error decoding access token")
        return

    showInfo(f'Signed in as {result_decode_token_access["payload"]["id_user"]}')


action_status = QAction("Status")
qconnect(action_status.triggered, on_status)

#: "Help" menu item


def on_help() -> None:
    openLink("mailto:support@rember.com")


action_help = QAction("Help")
qconnect(action_help.triggered, on_help)

#: "Rember" menu

if mw.pm is not None:
    menu_rember = mw.form.menuTools.addMenu("Rember")
    assert menu_rember is not None

    menu_rember.addAction(action_sign_in)
    menu_rember.addAction(action_status)
    menu_rember.addAction(action_help)
