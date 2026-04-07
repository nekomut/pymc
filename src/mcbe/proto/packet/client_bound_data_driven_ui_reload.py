"""Packet: ClientBoundDataDrivenUIReload."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_CLIENT_BOUND_DATA_DRIVEN_UI_RELOAD
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ClientBoundDataDrivenUIReload(Packet):
    packet_id = ID_CLIENT_BOUND_DATA_DRIVEN_UI_RELOAD
    pass

    def write(self, w: PacketWriter) -> None:
        pass

    @classmethod
    def read(cls, r: PacketReader) -> ClientBoundDataDrivenUIReload:
        return cls()
