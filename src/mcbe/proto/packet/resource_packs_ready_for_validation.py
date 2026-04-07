"""Packet: ResourcePacksReadyForValidation."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_RESOURCE_PACKS_READY_FOR_VALIDATION
from mcbe.proto.pool import Packet, register_bidirectional


@register_bidirectional
@dataclass
class ResourcePacksReadyForValidation(Packet):
    packet_id = ID_RESOURCE_PACKS_READY_FOR_VALIDATION

    def write(self, w: PacketWriter) -> None:
        pass

    @classmethod
    def read(cls, r: PacketReader) -> ResourcePacksReadyForValidation:
        return cls()
