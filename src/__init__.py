from aqt import appVersion

required_anki_version = (23, 10, 0)
anki_version = tuple(int(segment) for segment in appVersion.split("."))
if anki_version < required_anki_version:
    raise Exception(
        f"Minimum Anki version supported: {required_anki_version[0]}.{required_anki_version[1]}.{required_anki_version[2]}"
    )

from typing import Union

from aqt import gui_hooks, mw
from aqt.qt import QAction, qconnect
from aqt.utils import openLink, showInfo

from . import auth, auth_tokens

#: "Sign in"/"Log out" menu item

_auth: Union[auth.Auth, None] = None

action_sign_in = QAction("Sign in")
action_sign_in.setEnabled(False)


def init_auth():
    global _auth

    if mw.pm is None:
        raise Exception("ProfileManager not defined")

    def callback_state_auth(state: auth.StateAuth):
        action_sign_in.setEnabled(True)
        if state._tag == "LoggedOut":
            action_sign_in.setText("Sign in")
        if state._tag == "SigningIn":
            action_sign_in.setText("Cancel sign-in")
        if state._tag == "SignedIn":
            action_sign_in.setText("Log out")

    _auth = auth.Auth(mw=mw, pm=mw.pm, callback_state_auth=callback_state_auth)

    qconnect(action_sign_in.triggered, _auth.act_based_on_state)


def close_auth():
    global _auth

    if _auth is not None:
        _auth.close()
    _auth = None


gui_hooks.profile_did_open.append(init_auth)
gui_hooks.profile_will_close.append(close_auth)

#: "Status" menu item


def on_status() -> None:
    if mw.pm is None:
        raise Exception("ProfileManager not defined")

    tokens = auth_tokens.get_tokens(mw.pm)
    if tokens is None:
        showInfo("Logged out")
        return

    result_decode_token_access = auth_tokens.decode_token_access(tokens.access)
    if result_decode_token_access._tag == "ErrorTokens":
        showInfo("Error decoding access token")
        return

    showInfo(f"Signed in as {result_decode_token_access.payload.id_user}")

    # TODO:
    # url = "https://www.development.rember.com/api/v1/replicache-pull-for-anki"
    # json = {"version": "1", "versionSchema": "6", "cookie": None}
    # headers = {"authorization": f'Bearer {tokens["access"]}'}
    # response = requests.post(url, json=json, headers=headers)
    # print("Response")
    # print(f"Status: {response.status_code}")
    # print(f"JSON: {response.json()}")


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
