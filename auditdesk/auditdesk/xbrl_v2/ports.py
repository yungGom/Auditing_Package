"""I/O boundaries. Implementations live outside V2 domain and storage core."""
from __future__ import annotations

from typing import Protocol

from .model import SourceSnapshot


class SourceAcquisitionPort(Protocol):
    def acquire(self, logical_uri: str) -> bytes:
        """Return source bytes supplied by an external adapter."""


class SourceRepositoryPort(Protocol):
    def register(self, *, kind: str, logical_uri: str, data: bytes,
                 storage_location: str, parser_profile: str) -> SourceSnapshot:
        """Register immutable bytes, independent from path identity."""


class TaxonomyGraphStorePort(Protocol):
    def graph_snapshot(self, source_bundle_hash: str) -> object:
        """V2-2 graph snapshot lookup; no parsing in this phase."""
