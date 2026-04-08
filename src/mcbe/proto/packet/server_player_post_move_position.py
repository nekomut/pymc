"""Packet: ServerPlayerPostMovePosition.

Sent by the server to inform the client of the player's server-side
position at the end of movement.  Currently only used for debug draw.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_SERVER_PLAYER_POST_MOVE_POSITION
from mcbe.proto.pool import Packet, register_server_packet
from mcbe.proto.types import Vec3


@register_server_packet
@dataclass
class ServerPlayerPostMovePosition(Packet):
    packet_id = ID_SERVER_PLAYER_POST_MOVE_POSITION
    position: Vec3 = field(default_factory=Vec3)

    def write(self, w: PacketWriter) -> None:
        w.vec3(self.position)

    @classmethod
    def read(cls, r: PacketReader) -> ServerPlayerPostMovePosition:
        return cls(position=r.vec3())
