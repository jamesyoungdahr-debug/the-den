"""The Den's built-in BitTorrent client. `engine` is the one process-wide instance,
started/stopped from app.main's lifecycle hooks (same shape as app.scheduler)."""

from app.torrent.engine import EngineConfig, TorrentEngine, TorrentFile, TorrentStatus, engine

__all__ = ["EngineConfig", "TorrentEngine", "TorrentFile", "TorrentStatus", "engine"]
