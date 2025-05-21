import json
import os
from typing import Any, Dict

#:


class UserFiles:

    def __init__(self):

        dir_addon = os.path.dirname(os.path.realpath(__file__))
        dir_user_files = os.path.join(dir_addon, "user_files")

        if not os.path.exists(dir_user_files):
            raise FileNotFoundError(f"Directory '{dir_user_files}' does not exist")
        self.file_data_json = os.path.join(dir_user_files, "data.json")

        self._data: Dict[str, Any] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Load data from the JSON file if it exists."""
        if os.path.exists(self.file_data_json):
            try:
                with open(self.file_data_json, "r") as f:
                    self._data = json.load(f)
            except json.JSONDecodeError:
                self._data = {}
        else:
            self._data = {}

    def _save_data(self) -> None:
        """Save the current data to the JSON file."""
        with open(self.file_data_json, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value for the given key, returning default if key doesn't exist."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value for the given key and save to file."""
        self._data[key] = value
        self._save_data()

    def delete(self, key: str) -> None:
        """Delete a key-value pair if it exists."""
        if key in self._data:
            del self._data[key]
            self._save_data()

    def get_all(self) -> Dict[str, Any]:
        """Get all key-value pairs."""
        return self._data.copy()

    def clear(self) -> None:
        """Clear all data."""
        self._data.clear()
        self._save_data()
