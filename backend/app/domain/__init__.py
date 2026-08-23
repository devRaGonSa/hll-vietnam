"""HLL Vietnam domain types shared by infrastructure adapters and services."""

from .identity import PlayerId, PlayerIdentity, player_id_from

__all__ = ["PlayerId", "PlayerIdentity", "player_id_from"]
