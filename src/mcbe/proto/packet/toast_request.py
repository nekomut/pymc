"""Packet: ToastRequest."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_TOAST_REQUEST
from mcbe.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ToastRequest(Packet):
    packet_id = ID_TOAST_REQUEST
    title: str = ""
    message: str = ""

    def write(self, w: PacketWriter) -> None:
        w.string(self.title)
        w.string(self.message)

    @classmethod
    def read(cls, r: PacketReader) -> ToastRequest:
        return cls(
            title=r.string(),
            message=r.string(),
        )
