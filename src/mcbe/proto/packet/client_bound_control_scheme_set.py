"""Packet: ClientBoundControlSchemeSet."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_CLIENT_BOUND_CONTROL_SCHEME_SET
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ClientBoundControlSchemeSet(Packet):
    packet_id = ID_CLIENT_BOUND_CONTROL_SCHEME_SET
    control_scheme: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.control_scheme)

    @classmethod
    def read(cls, r: PacketReader) -> ClientBoundControlSchemeSet:
        return cls(
            control_scheme=r.uint8(),
        )
