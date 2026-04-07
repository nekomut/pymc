"""ClientCacheStatus packet - client reports cache support."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_CLIENT_CACHE_STATUS
from mcbe.proto.pool import Packet, register_bidirectional


@register_bidirectional
@dataclass
class ClientCacheStatus(Packet):
    packet_id = ID_CLIENT_CACHE_STATUS
    enabled: bool = False

    def write(self, w: PacketWriter) -> None:
        w.bool(self.enabled)

    @classmethod
    def read(cls, r: PacketReader) -> ClientCacheStatus:
        return cls(enabled=r.bool())
