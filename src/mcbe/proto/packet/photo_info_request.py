"""Packet: PhotoInfoRequest."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_PHOTO_INFO_REQUEST
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PhotoInfoRequest(Packet):
    packet_id = ID_PHOTO_INFO_REQUEST
    photo_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.photo_id)

    @classmethod
    def read(cls, r: PacketReader) -> PhotoInfoRequest:
        return cls(
            photo_id=r.varint64(),
        )
