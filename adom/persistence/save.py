"""Single-save permadeath service (design plan §3.3).

There is **one canonical save per character**.  On load the save file is
**deleted** from disk (so a crash/kill can't be reloaded); the game
re-saves on a clean quit.  Death erases the save.

All permadeath enforcement lives here behind a single ``permadeath``
flag, matching the plan's requirement to gate the whole subsystem on the
difficulty toggle (§5.7).  A run is serialized to JSON — the map itself
is regenerated from the stored seed + depth on load, so saves stay tiny
and deterministic.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


SAVE_DIR = os.environ.get(
    "ADOM_SAVE_DIR",
    os.path.join(os.path.expanduser("~"), ".adom_saves"),
)


@dataclass
class SaveService:
    permadeath: bool = True

    def _path(self, name: str) -> str:
        safe = "".join(c for c in name if c.isalnum() or c in "-_") or "hero"
        return os.path.join(SAVE_DIR, f"{safe}.json")

    def exists(self, name: str) -> bool:
        return os.path.exists(self._path(name))

    def save(self, name: str, state: dict) -> None:
        os.makedirs(SAVE_DIR, exist_ok=True)
        with open(self._path(name), "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, default=_json_default)

    def load(self, name: str) -> "dict | None":
        path = self._path(name)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)
        # Permadeath: consume the save on load so it can't be reused.
        if self.permadeath:
            os.remove(path)
        return state

    def erase(self, name: str) -> None:
        path = self._path(name)
        if os.path.exists(path):
            os.remove(path)

    def on_death(self, name: str) -> None:
        """Death ends the run — the save is gone under permadeath."""
        if self.permadeath:
            self.erase(name)


def _json_default(obj):
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError(f"Cannot serialize {type(obj)}")
