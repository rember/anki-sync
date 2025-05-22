from typing import Union

from . import user_files

#:


class CookieReplicache:

    def __init__(self, user_files: user_files.UserFiles):
        self._user_files = user_files

    def get(self) -> Union[int, None]:
        value = self._user_files.get("cookie_replicache")
        if value is not None and not isinstance(value, int):
            raise ValueError("cookie_replicache must be an integer or None")
        return value

    def set(self, cookie_replicache: Union[int, None]) -> None:
        self._user_files.set("cookie_replicache", cookie_replicache)

    def reset(self) -> None:
        self.set(None)
