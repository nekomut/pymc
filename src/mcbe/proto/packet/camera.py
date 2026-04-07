"""Packet: Camera."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_CAMERA
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class Camera(Packet):
    packet_id = ID_CAMERA
    camera_entity_unique_id: int = 0
    target_player_unique_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.camera_entity_unique_id)
        w.varint64(self.target_player_unique_id)

    @classmethod
    def read(cls, r: PacketReader) -> Camera:
        return cls(
            camera_entity_unique_id=r.varint64(),
            target_player_unique_id=r.varint64(),
        )
