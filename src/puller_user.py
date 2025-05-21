from typing import Optional

from .user_files import UserFiles
from .rember_client import Patch

#: put_user


def put_user(user_files: UserFiles, key: str, value: dict) -> None:
    user_files.set(key, value)


#: del_user


def del_user(user_files: UserFiles, key: str) -> None:
    raise RuntimeError("Deleting user data is not supported")


#: clear_users


def clear_users(user_files: UserFiles, patch: Patch) -> None:
    # Clear all user data
    for key in user_files.get_all():
        if key.startswith("User/"):
            user_files.delete(key)

    # Find user put operations
    user_put_ops = [
        op for op in patch if op["op"] == "put" and op["key"].startswith("User/")
    ]
    if len(user_put_ops) != 1:
        raise RuntimeError("Expected exactly one user put operation")

    # Apply the user put operation
    put_user(user_files, user_put_ops[0]["key"], user_put_ops[0]["value"])


#: get_user_email


def get_user_email(user_files: UserFiles) -> Optional[str]:
    for key in user_files.get_all():
        if key.startswith("User/"):
            user_data = user_files.get(key)
            if (
                user_data
                and "email" in user_data
                and isinstance(user_data["email"], str)
            ):
                return user_data["email"]
    return None
