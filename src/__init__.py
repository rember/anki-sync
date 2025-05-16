from aqt import mw
from aqt.utils import showInfo
from aqt.qt import *  # type: ignore

from . import auth_tokens


def testFunction() -> None:
    assert mw.col is not None

    auth_tokens.set_tokens(mw.pm, {"access": "foo", "refresh": "bar"})
    tokens = auth_tokens.get_tokens(mw.pm)
    showInfo(f"Stored tokens: {tokens}")

    cardCount = mw.col.card_count()
    showInfo("Card count: %d" % cardCount)


action = QAction("test", mw)
qconnect(action.triggered, testFunction)
mw.form.menuTools.addAction(action)
