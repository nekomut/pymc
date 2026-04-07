"""Packet: LocatorBar."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_LOCATOR_BAR
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class LocatorBar(Packet):
    packet_id = ID_LOCATOR_BAR
    waypoints: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.waypoints)

    @classmethod
    def read(cls, r: PacketReader) -> LocatorBar:
        return cls(
            waypoints=r.byte_slice(),
        )
