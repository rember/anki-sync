from anki import collection
from aqt import mw

#:

NAME_DECK_REMBER = "Rember"

#:


class Decks:
    def __init__(self, col: collection.Collection):
        self._col = col

    ##: create_deck_rember

    def create_deck_rember(self):
        """Creates the global "Rember" deck as the parent deck for all rembs
        imported from Rember.com. Decks imported from Rember will be created
        as subdecks nested under "Rember" (e.g., "Rember::Biology", "Rember::History").
        """
        decks = self._col.decks

        # Skip if the deck already exists
        if decks.by_name(NAME_DECK_REMBER) is not None:
            return

        deck = decks.new_deck_legacy(False)
        deck["name"] = NAME_DECK_REMBER
        deck["desc"] = (
            """This deck includes rembs and cards exported from <a href="https://www.rember.com/">Rember</a>."""
        )

        decks.add_deck_legacy(deck)

    ##: get_deck_rember

    def get_deck_rember(self):
        deck = self._col.decks.by_name(NAME_DECK_REMBER)
        if deck is None:
            raise RuntimeError("Rember deck not found")
        return deck
