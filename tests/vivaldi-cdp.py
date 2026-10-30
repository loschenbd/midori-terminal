#!/usr/bin/env python3
"""Two CDP errands tests/vivaldi-sandbox.sh needs: is it up, and shut it down.

A SEPARATE FILE, NOT A HEREDOC, FOR A REASON WORTH WRITING DOWN. These started
life inside `<<-'PY'` blocks in the shell script. `<<-` strips EVERY leading
tab, not one level of them, so tab-indented Python comes out with its nesting
flattened -- `try:` and the line under it both land in column 0 and Python
raises "IndentationError: expected an indented block". The shell happily loops
on the failure, so the symptom is a timeout ("#browser never appeared"), not a
syntax error anyone would look for.

    vivaldi-cdp.py up [port]      -> prints "up" once #browser exists, else ""
    vivaldi-cdp.py close [port]   -> Browser.close, by port and never by name

CLOSE BY PORT, NEVER BY NAME. `pkill Vivaldi` or `tell application "Vivaldi"
to quit` reaches whichever Vivaldi macOS feels like, which during development
is the operator's own browser. The debugging port identifies exactly one
instance.
"""
import json
import sys
import urllib.request

import websocket                      # not stdlib; the sandbox venv has it


def targets(port):
    return json.load(urllib.request.urlopen(f"http://localhost:{port}/json"))


def connect(url):
    return websocket.create_connection(url, timeout=20, suppress_origin=True)


def up(port):
    """A port that answers is not a UI that exists.

    Vivaldi's own bundle builds #browser well after the debugging port opens.
    A probe that runs in between reads null and reports an absent DOM rather
    than a slow one, which is why the sandbox polls this instead of sleeping.
    """
    ui = [t for t in targets(port) if t.get("url", "").endswith("window.html")]
    if not ui:
        return ""
    ws = connect(ui[0]["webSocketDebuggerUrl"])
    try:
        ws.send(json.dumps({
            "id": 1, "method": "Runtime.evaluate",
            "params": {"expression": "!!document.getElementById('browser')",
                       "returnByValue": True}}))
        return "up" if json.loads(ws.recv())["result"]["result"]["value"] else ""
    finally:
        ws.close()


def close(port):
    v = json.load(urllib.request.urlopen(
        f"http://localhost:{port}/json/version"))
    ws = connect(v["webSocketDebuggerUrl"])
    ws.send(json.dumps({"id": 1, "method": "Browser.close"}))
    try:
        ws.recv()
    except Exception:
        pass            # the socket goes away with the browser; expected
    return ""


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "up"
    port = sys.argv[2] if len(sys.argv) > 2 else "9222"
    try:
        print({"up": up, "close": close}[what](port), end="")
    except KeyError:
        sys.exit(f"unknown command {what!r}; want up or close")
    except Exception:
        print("", end="")       # unreachable browser is "not up", not a crash
