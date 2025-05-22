import json
from typing import Optional

from anki import collection, notes

from . import decks, models
from .puller_client import Patch

#:


class Rembs:

    def __init__(self, col: collection.Collection):
        self._col = col
        self._notetype = models.get_model_rember()
        self._deck = decks.get_deck_rember()

    ##: process_patch

    def process_patch(self, patch: Patch) -> None:
        rembs_to_create: list[dict] = []
        rembs_to_update: list[dict] = []
        ids_remb_to_delete: set[str] = set()

        for ix, op in enumerate(patch):

            # clear

            if op["op"] == "clear":
                if ix != 0:
                    raise RuntimeError(f"Unexpected 'clear' op in position {ix}")
                # Find all notes using the Rember model and mark them for deletion.
                # Later, if we encounter a "put" operation for any of these notes,
                # we'll remove them from the deletion list since they should be kept.
                ids_remb = self._find_ids_remb_by_id_model(self._notetype["id"])
                ids_remb_to_delete.update(ids_remb)

            # del

            if op["op"] == "del":
                if not op["key"].startswith("Remb/"):
                    continue
                id_remb = self._id_remb_from_key(op["key"])
                ids_remb_to_delete.add(id_remb)

            # put

            if op["op"] == "put":
                if not op["key"].startswith("Remb/"):
                    continue
                id_remb = self._id_remb_from_key(op["key"])
                id_note = self._id_note_by_guid(id_remb)
                value = op["value"]
                if id_note is None:
                    rembs_to_create.append(value)
                else:
                    value["id_note"] = id_note
                    rembs_to_update.append(value)

        # Remove rembs that will be created/updated from the deletion set
        ids_remb_to_delete -= {remb["id"] for remb in rembs_to_create + rembs_to_update}

        self._create_rembs(rembs_to_create)
        self._update_rembs(rembs_to_update)
        self._delete_rembs(ids_remb_to_delete)

    def _create_rembs(self, rembs: list[dict]):
        _notes: list[collection.AddNoteRequest] = []

        for remb in rembs:
            id_remb = remb["id"]

            content_remb = remb["content"]
            if not isinstance(content_remb, dict):
                raise ValueError(
                    "Invalid remb content, expected 'content' to be a dictionary"
                )

            ids_card = self._ids_card_from_content_remb(content_remb)

            note = self._col.new_note(self._notetype)
            # Anki overwrites note with the same guid. We use the Rember remb id as guid
            # to identify Anki notes.
            # REFS: https://github.com/kerrickstaley/genanki#note-guids
            note.guid = id_remb

            self._set_note_fields(note, id_remb, content_remb, ids_card)

            _notes.append(
                collection.AddNoteRequest(note=note, deck_id=self._deck["id"])
            )

        self._col.add_notes(_notes)

    def _update_rembs(self, rembs: list[dict]):
        _notes: list[notes.Note] = []

        for remb in rembs:
            id_remb = remb["id"]
            id_note = remb["id_note"]  # Set above in self.process_patch
            if id_note is None:
                raise RuntimeError("Unreachable. 'id_note' not set.")

            content_remb = remb["content"]
            if not isinstance(content_remb, dict):
                raise ValueError(
                    "Invalid remb content, expected 'content' to be a dictionary"
                )

            ids_card = self._ids_card_from_content_remb(content_remb)

            note = self._col.get_note(notes.NoteId(id_note))
            if note.guid != id_remb:
                raise RuntimeError("Unreachable. 'note.guid' does not match remb id.")

            self._set_note_fields(note, id_remb, content_remb, ids_card)

            _notes.append(note)

        self._col.update_notes(_notes, skip_undo_entry=True)

    def _delete_rembs(self, ids_remb: set[str]):
        ids_note = [self._id_note_by_guid(id_remb) for id_remb in ids_remb]
        ids_note = [
            notes.NoteId(id_note) for id_note in ids_note if id_note is not None
        ]
        if ids_note:
            self._col.remove_notes(ids_note)

    def _set_note_fields(
        self, note: notes.Note, id_remb: str, content_remb: dict, ids_card: list[str]
    ):
        field_link = f"""<a href="https://rember.com/r/${id_remb}">Edit in Rember (Remb ${id_remb})</a>"""
        note[models.NAME_FIELD_LINK] = field_link

        field_note = content_remb["note"]["text"]["textPlain"]
        if not isinstance(field_note, str):
            raise ValueError("Invalid remb content, 'textPlain' not found.")
        note[models.NAME_FIELD_NOTE] = field_note

        field_data = models.wrap_field_data(json.dumps(content_remb))
        note[models.NAME_FIELD_DATA] = field_data

        # Compute map id_card -> ix_field
        map_id_card_ix_field = self._compute_map_id_card_ix_field(note, ids_card)
        # Clear all fields first
        for ix_field in range(models.CNT_MAX_ANKI_CARDS):
            note[models.NAME_FIELD_ID_CARD(ix_field)] = ""
        # Set the id_card in fields according to the map
        for id_card, ix_field in map_id_card_ix_field.items():
            note[models.NAME_FIELD_ID_CARD(ix_field)] = id_card

        field_media = ""  # Media are currently not supported in Rember
        note[models.NAME_FIELD_MEDIA] = field_media

    def _compute_map_id_card_ix_field(
        self, note: notes.Note, ids_card: list[str]
    ) -> dict[str, int]:
        """See README.md section "Preserving the review history when a remb is edited"."""
        # Read current state from existing fields
        map_id_card_ix_field_prev = {}  # id_card -> ix_field
        ixs_field_prev = set()

        for ix_field in range(models.CNT_MAX_ANKI_CARDS):
            id_card = note[models.NAME_FIELD_ID_CARD(ix_field)]
            if id_card:  # field has a card
                if id_card in map_id_card_ix_field_prev:
                    # Handle duplicate card IDs - keep the first occurrence
                    continue
                map_id_card_ix_field_prev[id_card] = ix_field
                ixs_field_prev.add(ix_field)

        # Find the high water mark
        ix_field_max_prev = max(ixs_field_prev) if ixs_field_prev else -1

        # Preserve existing mappings for cards that still exist
        map_id_card_ix_field = {}
        for id_card in ids_card:
            if id_card in map_id_card_ix_field_prev:
                map_id_card_ix_field[id_card] = map_id_card_ix_field_prev[id_card]

        # Assign new cards starting from max + 1
        ix_field = ix_field_max_prev + 1
        for id_card in ids_card:
            if id_card not in map_id_card_ix_field:
                if ix_field >= models.CNT_MAX_ANKI_CARDS:
                    raise RuntimeError(
                        f"Field limit exceeded: cannot assign field {ix_field} (limit is {models.CNT_MAX_ANKI_CARDS}). This remb has used too many card slots over its lifetime."
                    )
                map_id_card_ix_field[id_card] = ix_field
                ix_field += 1

        return map_id_card_ix_field

    ##: Utils

    def _id_remb_from_key(self, key: str) -> str:
        return key[len("Remb/") :]

    def _ids_card_from_content_remb(self, content_remb: dict) -> list[str]:
        """
        Extract card IDs from a Remb's content, see `computeIdsCards` in @rember/editor-remb.

        Note: This implementation has to manually handle each crop type and extract tokens,
        which is error-prone and requires updating whenever new crop types are added.
        Ideally this logic would be shared with the editor-remb package.

        Args:
            content_remb (dict): The content dictionary of a Remb containing crops and occlusions.

        Returns:
            list[str]: List of card IDs in the format {id_crop}-{token}

        Raises:
            ValueError: If the content_remb structure is invalid or contains unexpected crop types.
        """
        crops = content_remb["crops"]
        if not isinstance(crops, list):
            raise ValueError("Invalid remb content, expected 'crops' to be a list")

        ids_card = []

        for crop in crops:
            id_crop = crop["id"]
            if not isinstance(id_crop, str):
                raise ValueError(
                    "Invalid remb content, expected crop 'id' to be a string"
                )

            type_crop = crop["type"]
            if not isinstance(type_crop, str):
                raise ValueError(
                    "Invalid remb content, expected crop 'type' to be a string"
                )

            if type_crop == "qa":
                tokens = ["default"]
            elif type_crop == "occlusion-text":
                occlusions = crop["occlusions"]
                if not isinstance(occlusions, list):
                    raise ValueError(
                        "Invalid remb content, expected 'occlusions' to be a list"
                    )
                tokens = [occlusion["id"] for occlusion in occlusions]
            else:
                raise ValueError(
                    f"Invalid remb content, unexpected crop type: {type_crop}"
                )

            for token in tokens:
                ids_card.append(f"{id_crop}-{token}")

        return ids_card

    def _id_note_by_guid(self, guid: str) -> Optional[int]:
        db = self._col.db
        if db is None:
            raise RuntimeError("Database connection is None")

        return db.scalar(
            """select id from notes where guid = ?""",
            guid,
        )

    def _find_ids_note_by_id_model(self, id_model: int) -> list[int]:
        db = self._col.db
        if db is None:
            raise RuntimeError("Database connection is None")

        return db.list(
            """select id from notes where mid = ?""",
            id_model,
        )

    def _find_ids_remb_by_id_model(self, id_model: int) -> list[str]:
        db = self._col.db
        if db is None:
            raise RuntimeError("Database connection is None")

        return db.list(
            """select guid from notes where mid = ?""",
            id_model,
        )
