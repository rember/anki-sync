import logging
import os
from datetime import datetime
from typing import Optional, Union

from . import auth_tokens, user_files, version

#:


class Logger:
    def __init__(self, user_files: user_files.UserFiles):
        self._user_files = user_files
        self._setup_logger()

    def _setup_logger(self):
        """Set up the logger to write to rember.log in the user_files directory."""
        # Get the user_files directory path
        path_addon = os.path.dirname(os.path.realpath(__file__))
        path_user_files = os.path.join(path_addon, "user_files")
        log_file = os.path.join(path_user_files, "rember.log")

        # Create logger
        self._logger = logging.getLogger("rember_anki_sync")
        self._logger.setLevel(logging.INFO)

        # Clear existing handlers to avoid duplicates
        self._logger.handlers.clear()

        # Create file handler
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)

        # Add handler to logger
        self._logger.addHandler(file_handler)

    def _get_context_info(self, mw=None) -> str:
        """Get context information like user ID and cookie replicache."""
        context_parts = []

        # Add version
        context_parts.append(f"v{version.VERSION_REMBER_ANKI_SYNC}")

        # Try to get user ID from tokens
        if mw and mw.pm:
            try:
                tokens = auth_tokens.get_tokens(mw.pm)
                if tokens:
                    result_decode = auth_tokens.decode_token_access(tokens.access)
                    if result_decode._tag == "Success":
                        context_parts.append(f"user_id={result_decode.payload.id_user}")
            except Exception:
                # Don't let context gathering fail the logging
                pass

        # Add cookie replicache
        try:
            cookie = self._user_files.get("cookie_replicache")
            if cookie is not None:
                context_parts.append(f"cookie_replicache={cookie}")
            else:
                context_parts.append("cookie_replicache=None")
        except Exception:
            # Don't let context gathering fail the logging
            pass

        return f"[{', '.join(context_parts)}]" if context_parts else ""

    def info(self, message: str, mw=None):
        """Log an info message with context."""
        context = self._get_context_info(mw)
        self._logger.info(f"{context} {message}")

    def warn(self, message: str, mw=None):
        """Log a warning message with context."""
        context = self._get_context_info(mw)
        self._logger.warning(f"{context} {message}")

    def error(self, message: str, mw=None, exception: Optional[Exception] = None):
        """Log an error message with context and optional exception details."""
        context = self._get_context_info(mw)
        error_msg = f"{context} {message}"

        if exception:
            error_msg += f" - Exception: {type(exception).__name__}: {str(exception)}"

        self._logger.error(error_msg)
