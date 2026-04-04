"""RakNet接続デバッグ.

バイトレベルでRakNet接続の全フローをトレースする。
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import struct
import time

# 詳細ログ有効化
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(message)s")

from pymc.raknet import RakNetNetwork
from pymc.raknet.connection import RakNetClientConnection, RakNetClientProtocol, _current_time_ms
from pymc.raknet.protocol import (
    FRAME_SET_MIN, FRAME_SET_MAX, ACK, NACK,
    CONNECTION_REQUEST, CONNECTION_REQUEST_ACCEPTED,
    GAME_PACKET, decode_frame_set,
)

logger = logging.getLogger("debug")


class TracingProtocol(RakNetClientProtocol):
    """送受信バイトをすべてログ出力するプロトコル."""

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        pkt_id = data[0] if data else -1
        logger.info("<<< RECV %d bytes from %s, pkt_id=0x%02x, hex=%s",
                     len(data), addr, pkt_id, data[:40].hex())

        # フレームセットならフレーム内容もダンプ
        if FRAME_SET_MIN <= pkt_id <= FRAME_SET_MAX:
            try:
                seq, frames = decode_frame_set(data)
                for i, f in enumerate(frames):
                    logger.info("    frame[%d] reliability=%d body_len=%d body_hex=%s",
                                i, f.reliability, len(f.body), f.body[:30].hex())
            except Exception as e:
                logger.warning("    frame decode error: %s", e)

        super().datagram_received(data, addr)

    def send(self, data: bytes, addr: tuple[str, int]) -> None:
        pkt_id = data[0] if data else -1
        logger.info(">>> SEND %d bytes to %s, pkt_id=0x%02x, hex=%s",
                     len(data), addr, pkt_id, data[:40].hex())

        if FRAME_SET_MIN <= pkt_id <= FRAME_SET_MAX:
            try:
                seq, frames = decode_frame_set(data)
                for i, f in enumerate(frames):
                    logger.info("    frame[%d] reliability=%d body_len=%d body_hex=%s",
                                i, f.reliability, len(f.body), f.body[:30].hex())
            except Exception as e:
                logger.warning("    frame decode error: %s", e)

        super().send(data, addr)


async def main(address: str) -> None:
    host, port_str = address.rsplit(":", 1)
    port = int(port_str)
    remote_addr = (host, port)

    network = RakNetNetwork()

    # Step 1: Ping
    try:
        pong = await network.ping(address)
        print(f"Ping OK: {pong.decode()[:80]}")
    except Exception as e:
        print(f"Ping NG: {e}")
        return

    # Step 2: Manual connection with tracing
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        TracingProtocol,
        remote_addr=None,
        local_addr=("0.0.0.0", 0),
    )
    local_addr = transport.get_extra_info("sockname", ("0.0.0.0", 0))
    print(f"Local: {local_addr}")

    try:
        # Offline handshake
        mtu, server_guid = await network._offline_handshake(protocol, remote_addr)
        print(f"Offline handshake OK: MTU={mtu}, guid={server_guid}")

        # Create connection
        conn = RakNetClientConnection(
            protocol=protocol,
            remote_addr=remote_addr,
            local_addr=local_addr,
            mtu=mtu,
            client_guid=network._client_guid,
            server_guid=server_guid,
        )
        conn.start()

        # Send ConnectionRequest
        print("Sending ConnectionRequest...")
        await network._send_connection_request(conn)

        # Wait for ConnectionRequestAccepted
        print("Waiting for ConnectionRequestAccepted...")
        try:
            await asyncio.wait_for(conn._connected.wait(), timeout=5.0)
            print("ConnectionRequestAccepted received!")
        except asyncio.TimeoutError:
            print("TIMEOUT waiting for ConnectionRequestAccepted")
            # ダンプ状態
            print(f"  recv_queue size: {protocol._recv_queue.qsize()}")
            print(f"  game_packets size: {conn._game_packets.qsize()}")
            print(f"  ack_queue: {conn._ack_queue}")
            print(f"  expected_seq: {conn._expected_seq}")
            return

        # Send RequestNetworkSettings (game packet)
        print("Sending RequestNetworkSettings...")
        # write_packet now sends data as-is (no 0xFE prefix added)
        # batch format: 0xFE (header) + varuint(length=6) + varuint(packet_id=193) + be_int32(944)
        batch = b"\xfe\x06\xc1\x01" + struct.pack(">I", 944)
        await conn.write_packet(batch)

        # Wait for response
        print("Waiting for game packet response...")
        try:
            data = await asyncio.wait_for(conn._game_packets.get(), timeout=5.0)
            print(f"Game packet received: {len(data)} bytes, hex={data[:30].hex()}")
        except asyncio.TimeoutError:
            print("TIMEOUT waiting for game packet")

    finally:
        transport.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="127.0.0.1:19132")
    args = parser.parse_args()
    asyncio.run(main(args.address))
