"""Packet: TickingAreasLoadStatus."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_TICKING_AREAS_LOAD_STATUS
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class TickingAreasLoadStatus(Packet):
    packet_id = ID_TICKING_AREAS_LOAD_STATUS
    preload: bool = False

    def write(self, w: PacketWriter) -> None:
        w.bool(self.preload)

    @classmethod
    def read(cls, r: PacketReader) -> TickingAreasLoadStatus:
        return cls(
            preload=r.bool(),
        )
