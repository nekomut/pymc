"""Packet: CommandOutput."""

from __future__ import annotations

from dataclasses import dataclass, field

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_COMMAND_OUTPUT
from mcbe.proto.packet.command_request import CommandOrigin
from mcbe.proto.pool import Packet, register_server_packet


@dataclass
class CommandOutputMessage:
    """A single message within CommandOutput."""
    message_id: str = ""
    success: bool = False
    parameters: list[str] = field(default_factory=list)


@register_server_packet
@dataclass
class CommandOutput(Packet):
    packet_id = ID_COMMAND_OUTPUT
    command_origin: CommandOrigin = field(default_factory=CommandOrigin)
    output_type: str = ""
    success_count: int = 0
    output_messages: list[CommandOutputMessage] = field(default_factory=list)
    data_set: str = ""

    def write(self, w: PacketWriter) -> None:
        self.command_origin.write(w)
        w.string(self.output_type)
        w.uint32(self.success_count)
        w.varuint32(len(self.output_messages))
        for msg in self.output_messages:
            w.string(msg.message_id)
            w.bool(msg.success)
            w.varuint32(len(msg.parameters))
            for p in msg.parameters:
                w.string(p)
        if self.output_type == "dataset":
            w.varuint32(1)
            w.string(self.data_set)

    @classmethod
    def read(cls, r: PacketReader) -> CommandOutput:
        command_origin = CommandOrigin.read(r)
        output_type = r.string()
        success_count = r.uint32()
        msg_count = r.varuint32()
        messages = []
        for _ in range(msg_count):
            message_id = r.string()
            success = r.bool()
            param_count = r.varuint32()
            params = [r.string() for _ in range(param_count)]
            messages.append(CommandOutputMessage(
                message_id=message_id, success=success, parameters=params,
            ))
        data_set = ""
        if output_type == "dataset":
            r.varuint32()  # count (always 1)
            data_set = r.string()
        return cls(
            command_origin=command_origin,
            output_type=output_type,
            success_count=success_count,
            output_messages=messages,
            data_set=data_set,
        )
