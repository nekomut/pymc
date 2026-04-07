"""Packet: ClientBoundDataStore."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_CLIENT_BOUND_DATA_STORE
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ClientBoundDataStore(Packet):
    packet_id = ID_CLIENT_BOUND_DATA_STORE
    updates: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.updates)

    @classmethod
    def read(cls, r: PacketReader) -> ClientBoundDataStore:
        return cls(
            updates=r.byte_slice(),
        )
