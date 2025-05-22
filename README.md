# Anki Add-on to sync flashcards from Rember

## Setup

- Clone the repo.

- Copy `.env.example` to `.env` and fill the variables.

- Install [Nix](https://nixos.org/).

- Run `nix develop -c $SHELL` to start a development shell. This happens automatically if you use [direnv](https://direnv.net/).

## Tasks

Run `make dev` to createa `rember-anki-sync-dev` add-on in Anki, which you can use to test the add-on after making changes.

Run `make zip` to create a `rember-anki-sync.zip` file which can be uploaded to [AnkiWeb](https://ankiweb.net/shared/addons).

Run `make update-app-anki` to update the `src/app_anki` folder, it assumes that the private `rember` repo lives next to the project folder.

## Notes

We use Python 3.9 because that's the version currently used in the Anki repo.

We install packages with `uv` only for type checking, the code is currently only executed by Anki.

Users sign up with their Rember account following the best practices described in [RFC 8252 - OAuth 2.0 for Native Apps](https://datatracker.ietf.org/doc/html/rfc8252): we use the authorization code grant with PKCE in an external browser and use the loopback interface to receive the OAuth redirect. Once we obtain auth tokens, we store them in the user profile. Anki stores AnkiWeb and AnkiHub auth tokens in the user profile as plain text, see for example [`sync_login`](https://github.com/ankitects/anki/blob/d3d6bd8ce006f178e2271fd8d317fdc8832095df/qt/aqt/sync.py#L320-L321).

The `src/app_anki` folder contains the bundle for the `@rember/app-anki` package in the private `rember` repository. It's included in this repository using Git LFS and is used in the Rember note templates.

### Preserving the review history when a remb changes

**Problem**: The Anki review history breaks if a remb is updated and the card ids order changes (eg. crop order changes, card tokens order changes, crop is deleted). The reason is that review histories are associated to Anki cards, and Anki cards are associated to note templates by index (the `ord` property in the Anki card).

For example:

- _Student imports a remb_: Remb v1 has card ids `["c0", "c1"]`, the Anki note contains fields `Card #0: "c0", Card #1: "c1", Card #2: "", ...`. The Anki card with `ord: 0` is associated with template "Card #0" of the Anki note, and renders the card "c0".
- _Student reviews the Anki card with `ord: 0`_
- _Student updates the remb_: Remb v2 has card ids `["c1", "c0", "c2"]`, the Anki note contains fields `Card #0: "c1", Card #1: "c0", Card #2: "c2", Card #3: "", ...`. The Anki card with `ord: 0` now renders "c1" instead of "c0"; the Anki card with `ord: 1` now renders "c0". The result is that "c1" gained a review that never happened and "c0" lost a review.

The limitation exists because Anki assumes that models are static, whereas we hack them to be dynamic.

**Solution**: We use monotonic field assignment where each card maintains the same field forever (and consequently the template), and field indices are never reused once assigned. This preserves Anki review history perfectly while requiring no external state (mappings are read from current fields) and handles all user actions: create, update, delete, reorder.

The algorithm uses a "high water mark" approach to support deletions safely:

On note update:

1. Read current card-to-field mappings from the existing note
2. Keep existing field positions for cards that still exist in the updated remb
3. Find the highest field index ever used as the "high water mark"
4. Assign new cards to field indices starting after the high water mark
5. Clear fields for deleted cards but never reuse those field indices

After all notes have been updated, we use Anki's built-in `get_empty_cards()` and `remove_cards_and_orphaned_notes()` functions to identify and remove empty cards of the Rember notetype. Since the field has been emptied, the card is now considered empty by Anki and is deleted to avoid cluttering the user's deck.

This approach has important tradeoffs. Field indices accumulate over time because deleted cards "burn" their indices permanently - when a card is deleted, its field is cleared but that index position is retired forever to prevent review history contamination. The high water mark ensures we never assign new cards to previously used indices, even if those fields are now empty.

See `_compute_map_id_card_ix_field()` in `src/rembs.py`. We use 100 fields to accommodate card churn over a Remb's lifetime.

## References

- [Anki GitHub](https://github.com/ankitects/anki/tree/main)
- [Anki Add-ons docs](https://addon-docs.ankiweb.net/intro.html)
- [RFC 8252 - OAuth 2.0 for Native Apps](https://datatracker.ietf.org/doc/html/rfc8252)
