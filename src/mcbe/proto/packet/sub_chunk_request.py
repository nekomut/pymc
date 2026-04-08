"""Packet: SubChunkRequest."""

from __future__ import annotations

from dataclasses import dataclass, field

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_SUB_CHUNK_REQUEST
from mcbe.proto.pool import Packet, register_client_packet
from mcbe.proto.types import SubChunkPos


@dataclass
class SubChunkOffset:
    x: int = 0
    y: int = 0
    z: int = 0


@register_client_packet
@dataclass
class SubChunkRequest(Packet):
    packet_id = ID_SUB_CHUNK_REQUEST
    dimension: int = 0
    position: SubChunkPos = field(default_factory=SubChunkPos)
    offsets: list[SubChunkOffset] = field(default_factory=list)

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.dimension)
        w.sub_chunk_pos(self.position)
        # uint32 count + count * (int8, int8, int8)
        w.uint32(len(self.offsets))
        for off in self.offsets:
            w.int8(off.x)
            w.int8(off.y)
            w.int8(off.z)

    @classmethod
    def read(cls, r: PacketReader) -> SubChunkRequest:
        dimension = r.varint32()
        position = r.sub_chunk_pos()
        count = r.uint32()
        offsets = []
        for _ in range(count):
            offsets.append(SubChunkOffset(
                x=r.int8(), y=r.int8(), z=r.int8(),
            ))
        return cls(dimension=dimension, position=position, offsets=offsets)
