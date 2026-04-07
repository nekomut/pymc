"""Packet: ShowProfile."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_SHOW_PROFILE
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ShowProfile(Packet):
    packet_id = ID_SHOW_PROFILE
    xuid: str = ""

    def write(self, w: PacketWriter) -> None:
        w.string(self.xuid)

    @classmethod
    def read(cls, r: PacketReader) -> ShowProfile:
        return cls(
            xuid=r.string(),
        )
