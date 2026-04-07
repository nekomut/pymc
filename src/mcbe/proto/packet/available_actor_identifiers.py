"""Packet: AvailableActorIdentifiers."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_AVAILABLE_ACTOR_IDENTIFIERS
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class AvailableActorIdentifiers(Packet):
    packet_id = ID_AVAILABLE_ACTOR_IDENTIFIERS
    serialised_entity_identifiers: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.bytes_raw(self.serialised_entity_identifiers)

    @classmethod
    def read(cls, r: PacketReader) -> AvailableActorIdentifiers:
        return cls(
            serialised_entity_identifiers=r.bytes_remaining(),
        )
