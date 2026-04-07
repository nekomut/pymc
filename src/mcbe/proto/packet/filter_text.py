"""Packet: FilterText."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_FILTER_TEXT
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class FilterText(Packet):
    packet_id = ID_FILTER_TEXT
    text: str = ""
    from_server: bool = False

    def write(self, w: PacketWriter) -> None:
        w.string(self.text)
        w.bool(self.from_server)

    @classmethod
    def read(cls, r: PacketReader) -> FilterText:
        return cls(
            text=r.string(),
            from_server=r.bool(),
        )
