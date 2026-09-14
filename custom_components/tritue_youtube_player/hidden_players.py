"""Players the card should not list, kept in Home Assistant storage.

Many homes expose far more ``media_player`` entities than anyone plays music on
(Cast groups, offline speakers, the integration's own virtual player). The card
lets an admin hide them; the list lives in ``.storage`` so it survives Home
Assistant restarts, card reloads and integration updates, and every hidden
player can be restored from the card.

Pure helpers only (no Home Assistant imports) so they run in the unit tests.
"""

from __future__ import annotations

import re
from typing import Any

MEDIA_PLAYER_ENTITY_ID = re.compile(r"^media_player\.[a-z0-9_]+$")
MAX_HIDDEN_PLAYERS = 500
STORAGE_VERSION = 1
STORAGE_KEY = "tritue_youtube_player.hidden_players"


def normalize_hidden(value: Any) -> list[str]:
    """Return the stored list with anything malformed dropped."""
    if isinstance(value, dict):
        value = value.get("entity_ids")
    if not isinstance(value, list):
        return []
    hidden: list[str] = []
    for candidate in value:
        entity_id = str(candidate or "")
        if MEDIA_PLAYER_ENTITY_ID.fullmatch(entity_id) and entity_id not in hidden:
            hidden.append(entity_id)
    return hidden[:MAX_HIDDEN_PLAYERS]


def apply_hidden_change(current: list[str], entity_ids: Any, hidden: Any) -> list[str]:
    """Hide (``hidden=True``) or restore players; raise ValueError on bad input."""
    if not isinstance(hidden, bool):
        raise ValueError("invalid_hidden_flag")
    if (
        not isinstance(entity_ids, list)
        or not 1 <= len(entity_ids) <= MAX_HIDDEN_PLAYERS
        or not all(
            isinstance(entity_id, str) and MEDIA_PLAYER_ENTITY_ID.fullmatch(entity_id)
            for entity_id in entity_ids
        )
    ):
        raise ValueError("invalid_target_entity")
    if hidden:
        result = list(current) + [e for e in entity_ids if e not in current]
        if len(set(result)) > MAX_HIDDEN_PLAYERS:
            raise ValueError("too_many_hidden_players")
        return normalize_hidden(result)
    removed = set(entity_ids)
    return [entity_id for entity_id in current if entity_id not in removed]
