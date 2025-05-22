# This file creates a global Rember deck which contains all of the user's rembs
# imported from Rember.com. The deck is created when the add-on loads and is
# used as the destination for all synced content.

from aqt import mw

#: Constants

NAME_DECK_REMBER = "Rember"

#:


def create_deck_rember():
    if mw.col is None:
        raise RuntimeError("Connection is None")

    decks = mw.col.decks

    # Skip if the deck already exists
    if decks.by_name(NAME_DECK_REMBER) is not None:
        return

    deck = decks.new_deck_legacy(False)
    deck["name"] = NAME_DECK_REMBER
    deck["desc"] = (
        """This deck includes rembs and cards exported from <a href="https://www.rember.com/">Rember</a>."""
    )

    decks.add_deck_legacy(deck)


#:


def get_deck_rember():
    if mw.col is None:
        raise RuntimeError("Connection is None")

    deck = mw.col.decks.by_name(NAME_DECK_REMBER)
    if deck is None:
        raise RuntimeError("Rember deck not found")

    return deck
