from aqt import appVersion

required_anki_version = (23, 10, 0)
anki_version = tuple(int(segment) for segment in appVersion.split("."))
if anki_version < required_anki_version:
    raise RuntimeError(
        f"Minimum Anki version supported: {required_anki_version[0]}.{required_anki_version[1]}.{required_anki_version[2]}"
    )

from aqt import gui_hooks, mw
from aqt.errors import show_exception
from aqt.qt import QAction, qconnect
from aqt.utils import openLink, showInfo

from . import (
    auth,
    auth_tokens,
    decks,
    info,
    logger,
    models,
    puller,
    puller_cookie_replicache,
    user_files,
    users,
)

#: Init


_user_files = user_files.UserFiles()
_user_files.set("version_rember_anki_sync", info.VERSION_REMBER_ANKI_SYNC)
_cookie_replicache = puller_cookie_replicache.CookieReplicache(user_files=_user_files)

_logger = logger.Logger(user_files=_user_files)

# Log plugin initialization
_logger.info(f"Plugin initialized", mw)

# Allow access to app-anki files to the webviews
# REFS: https://addon-docs.ankiweb.net/hooks-and-filters.html#managing-external-resources-in-webviews
mw.addonManager.setWebExports(__name__, r"app_anki/.*(css|js)")


# Create the "Rember X.X.X" model and the "Rember" deck
def on_load(_) -> None:
    if mw.col is None:
        raise RuntimeError("Collection is None")

    _models = models.Models(col=mw.col)
    _decks = decks.Decks(col=mw.col)
    _models.create_media_app_anki()
    _models.create_model_rember()
    _decks.create_deck_rember()


gui_hooks.collection_did_load.append(on_load)

#: Rember menu

action_auth = QAction("Sign in")
action_auth.setEnabled(False)

action_status = QAction("Status")

action_import_rember_data = QAction("Import Rember data")
action_auth.setEnabled(False)

action_help = QAction("Help")

if mw.pm is not None:
    menu_rember = mw.form.menuTools.addMenu("Rember")
    assert menu_rember is not None

    menu_rember.addAction(action_auth)
    menu_rember.addAction(action_status)
    menu_rember.addAction(action_import_rember_data)
    menu_rember.addAction(action_help)


#: Auth


def callback_state_auth(state: auth.StateAuth) -> None:
    if state._tag == "LoggedOut":
        action_auth.setText("Sign in")
        action_import_rember_data.setEnabled(False)
        # Clear cookie_replicache, so that we pull from scratch next time the
        # user signs in
        _cookie_replicache.reset()
        _logger.info("Cookie replicache reset, reason: user logged out", mw)

    if state._tag == "SigningIn":
        action_auth.setText("Cancel sign-in")
        action_import_rember_data.setEnabled(False)

    if state._tag == "SignedIn":
        action_auth.setText("Log out")
        action_import_rember_data.setEnabled(True)


_auth = auth.Auth(mw=mw, callback_state_auth=callback_state_auth, logger=_logger)


def refresh_auth() -> None:
    if mw.pm is None:
        raise RuntimeError("ProfileManager not defined")

    _auth.refresh_state_from_tokens()
    action_auth.setEnabled(True)


def close_auth() -> None:
    action_auth.setEnabled(False)
    action_import_rember_data.setEnabled(False)
    _auth.close()


gui_hooks.profile_did_open.append(refresh_auth)
gui_hooks.profile_will_close.append(close_auth)

#: Puller

_puller = puller.Puller(mw=mw, auth=_auth, user_files=_user_files, logger=_logger)

# WARN: We want to pull from Rember before syncing, so that the changes are
# are synced. In order for this to work as we expect, we rely on background
# operations that access collection being serialized in Anki.
gui_hooks.sync_will_start.append(_puller.pull)


#: Action triggers

##: action_auth


def on_action_auth() -> None:
    if _auth.state._tag == "LoggedOut":
        return _auth.sign_in()
    if _auth.state._tag == "SigningIn":
        return _auth.cancel_sign_in()
    if _auth.state._tag == "SignedIn":
        return _auth.log_out()


qconnect(action_auth.triggered, on_action_auth)

##: action_status


def on_action_status() -> None:
    if mw.pm is None:
        raise RuntimeError("ProfileManager not defined")

    if _auth.state._tag == "Unknown":
        return

    if _auth.state._tag == "LoggedOut" or _auth.state._tag == "SigningIn":
        showInfo("Logged out.")
        return

    result_decode_token_access = auth_tokens.decode_token_access(
        _auth.state.tokens.access
    )
    if result_decode_token_access._tag != "Success":
        _logger.error(
            f"Failed to decode access token. {result_decode_token_access._tag}: {result_decode_token_access.message}",
            mw,
        )
        show_exception(
            parent=mw,
            exception=RuntimeError(
                f"{result_decode_token_access._tag}: {result_decode_token_access.message}"
            ),
        )
        return

    _users = users.Users(user_files=_user_files)
    email = _users.get_email_user(id_user=result_decode_token_access.payload.id_user)

    if email is None:
        showInfo('Signed in, press the "Sync" button to sync Rember data.')
        return

    showInfo(f"Signed in as {email}")


qconnect(action_status.triggered, on_action_status)

##: `action_import_rember_data`


def on_action_import_rember_data() -> None:
    if mw.pm is None:
        raise RuntimeError("ProfileManager not defined")

    if _auth.state._tag != "SignedIn":
        raise RuntimeError("Unreachable. Menu action should be disabled")

    showInfo(
        "Importing your Rember data...\n\nNote: You don't need to import manually, the Rember add-on automatically imports your data whenever you sync Anki."
    )

    # Clear cookie_replicache, so that we pull from scratch when the user imports manually
    _cookie_replicache.reset()
    _logger.info("Cookie replicache reset, reason: manual import started", mw)

    # Pull
    _puller = puller.Puller(mw=mw, auth=_auth, user_files=_user_files, logger=_logger)
    _puller.pull()


qconnect(action_import_rember_data.triggered, on_action_import_rember_data)

##: `action_help`


def on_action_help() -> None:
    openLink("mailto:support@rember.com")


qconnect(action_help.triggered, on_action_help)
