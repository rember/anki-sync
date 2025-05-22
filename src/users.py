from typing import Optional

from . import user_files
from .rember_client import Patch

#:


class Users:

    def __init__(self, user_files: user_files.UserFiles):
        self._user_files = user_files

    ##: process_patch

    def process_patch(self, patch: Patch) -> None:
        for ix, op in enumerate(patch):

            # clear

            if op["op"] == "clear":
                if ix != 0:
                    raise RuntimeError(f"Unexpected 'clear' op in position {ix}")
                # Clear all user data
                for key in self._user_files.get_all():
                    if key.startswith("User/"):
                        self._user_files.delete(key)

            # del

            if op["op"] == "del":
                if not op["key"].startswith("User/"):
                    continue
                self._user_files.delete(key)

            # put

            if op["op"] == "put":
                if not op["key"].startswith("User/"):
                    continue
                self._user_files.set(key, op["value"])

    ##: get_email_user

    def get_email_user(self, id_user: str) -> Optional[str]:
        value = self._user_files.get(f"User/{id_user}")
        if value is None:
            return None

        if value and "email" in value and isinstance(value["email"], str):
            return value["email"]
        else:
            raise ValueError(
                f"Invalid data for user {id_user}. Email is missing or invalid."
            )
