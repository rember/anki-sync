import threading
import functools
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from typing import Optional, Tuple, Dict, Any, Callable, Union, Literal, TypedDict
import socket
import html

#: Handler


class DataAuth(TypedDict):
    code: str
    state: str


class _Handler(BaseHTTPRequestHandler):
    """Handles the OAuth callback, captures code and state, then signals server to stop."""

    def __init__(
        self,
        request: socket.socket,
        client_address: Tuple[str, int],
        server: HTTPServer,
        callback: Callable[[DataAuth], None],
    ):
        self._callback = callback
        super().__init__(request, client_address, server)

    def _send_response_html(self, title: str, message: str) -> None:
        """Sends a formatted HTML response to the client."""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html_template = """
        <html>
            <head>
                <meta charset='utf-8'>
                <title>{title}</title>
                <style>
                    body {{ font-family: sans-serif; margin: 20px; }}
                </style>
            </head>
            <body>
                <h1>{title}</h1>
                <p>{message}</p>
                <p>You can close this window and return to Anki.</p>
            </body>
        </html>
        """
        final_html = html_template.format(
            title=html.escape(title), message=html.escape(message)
        )
        self.wfile.write(final_html.encode("utf-8"))

    def do_GET(self) -> None:
        path_parsed = urlparse(self.path)
        params_query = parse_qs(path_parsed.query)

        code = params_query.get("code", [None])[0]
        state = params_query.get("state", [None])[0]

        if not isinstance(code, str) or not isinstance(state, str):
            self._send_response_html(
                "Invalid Request",
                "The request was invalid. Code and state parameters must be strings.",
            )
            raise Exception(
                "Invalid request: Code and state parameters must be strings."
            )

        self._send_response_html(
            "Authentication Successful!", "Your authentication was successful."
        )
        self._callback({"code": code, "state": state})

    # Suppress log messages to keep the console clean
    def log_message(self, format: str, *args: Any) -> None:
        return


#: ServerLoopback


class StateStarted(TypedDict):
    _tag: Literal["Started"]
    server_http: HTTPServer


class StateListening(TypedDict):
    _tag: Literal["Listening"]
    server_http: HTTPServer
    thread_server_http: threading.Thread
    event_done: threading.Event
    data_auth: Optional[DataAuth]


class StateShutdown(TypedDict):
    _tag: Literal["Shutdown"]


ServerState = Union[StateStarted, StateListening, StateShutdown]


class ServerLoopback:
    """A local HTTP server implementation for handling OAuth authentication callbacks.

    This class creates a temporary HTTP server on localhost with a dynamically assigned port
    to handle OAuth 2.0 authentication callbacks.

    Attributes:
        uri_redirect (str): The complete redirect URI (e.g., 'http://localhost:{port}/callback')
                          that should be used in the OAuth authorization request.

    The server goes through three states:
        - Started: Initial state after instantiation, server is created but not listening
        - Listening: Server is actively listening for the callback
        - Closed: Server has been shut down and can no longer be used
    """

    uri_redirect: str
    _state: ServerState

    def __init__(self):
        def callback(data_auth: DataAuth) -> None:
            if self._state["_tag"] != "Listening":
                # Silently ignore callbacks in non-listening state
                return
            self._state["data_auth"] = data_auth
            self._state["event_done"].set()

        try:
            server_http = HTTPServer(
                # We set the port to 0 to assign a free port
                ("localhost", 0),
                functools.partial(
                    _Handler,
                    callback=callback,
                ),
            )
        except Exception as e:
            self._state = {"_tag": "Shutdown"}
            raise RuntimeError(f"Failed to initialize HTTP server: {e}") from e

        self.uri_redirect = f"http://localhost:{server_http.server_port}/callback"
        self._state = {
            "_tag": "Started",
            "server_http": server_http,
        }

    def listen(self, timeout: Optional[float] = 120.0) -> DataAuth:
        if self._state["_tag"] != "Started":
            raise RuntimeError(f"Invalid state: {self._state['_tag']}")

        thread_server_http = threading.Thread(
            target=self._state["server_http"].serve_forever, daemon=True
        )
        event_done = threading.Event()

        self._state = {
            "_tag": "Listening",
            "server_http": self._state["server_http"],
            "thread_server_http": thread_server_http,
            "event_done": event_done,
            "data_auth": None,
        }

        try:
            thread_server_http.start()
            # Block until `event_done` is set
            if not event_done.wait(timeout):
                raise TimeoutError("Timed out waiting for authentication callback")

            if self._state["data_auth"] is None:
                raise RuntimeError("Authentication data not set")

            return self._state["data_auth"]
        finally:
            self.shutdown()

    def shutdown(self):
        try:
            if self._state["_tag"] == "Started":
                self._state["server_http"].shutdown()
                self._state["server_http"].server_close()

            if self._state["_tag"] == "Listening":
                self._state["event_done"].set()
                self._state["thread_server_http"].join(timeout=2.0)
                self._state["server_http"].shutdown()
                self._state["server_http"].server_close()

        finally:
            self._state = {"_tag": "Shutdown"}
