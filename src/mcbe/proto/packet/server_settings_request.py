"""Packet: ServerSettingsRequest."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_SERVER_SETTINGS_REQUEST
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ServerSettingsRequest(Packet):
    packet_id = ID_SERVER_SETTINGS_REQUEST
    pass

    def write(self, w: PacketWriter) -> None:
        pass

    @classmethod
    def read(cls, r: PacketReader) -> ServerSettingsRequest:
        return cls()
