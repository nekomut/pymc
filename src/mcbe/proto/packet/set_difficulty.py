"""Packet: SetDifficulty."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_SET_DIFFICULTY
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SetDifficulty(Packet):
    packet_id = ID_SET_DIFFICULTY
    difficulty: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.difficulty)

    @classmethod
    def read(cls, r: PacketReader) -> SetDifficulty:
        return cls(
            difficulty=r.varuint32(),
        )
