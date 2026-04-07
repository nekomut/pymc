"""NetherNet Network implementation using libdatachannel.

Uses the C++ native libdatachannel library instead of aiortc for
WebRTC DataChannel connections. This provides native SCTP/DTLS
implementation via usrsctp and OpenSSL, matching the behavior of
libwebrtc more closely than aiortc's pure Python implementation.
"""

from __future__ import annotations

import asyncio
import logging
import random

import libdatachannel as dc

from mcbe.nethernet.signaling import (
    SIGNAL_ANSWER,
    SIGNAL_CANDIDATE,
    SIGNAL_ERROR,
    SIGNAL_OFFER,
    JsonRpcSignaling,
    Signal,
    WebSocketSignaling,
    generate_network_id,
)
from mcbe.network import Network, NetworkConnection

logger = logging.getLogger(__name__)

# Maximum payload per segment (excluding the 1-byte header).
MAX_MESSAGE_SIZE = 10_000
MAX_SEGMENTS = 256


class LdcNetherNetConn(NetworkConnection):
    """NetherNet connection using libdatachannel DataChannels.

    Handles segmentation/reassembly using the NetherNet wire format:
    each segment is ``[remaining: uint8][payload]``.
    """

    def __init__(
        self,
        pc: dc.PeerConnection,
        reliable_dc: dc.DataChannel,
        unreliable_dc: dc.DataChannel | None = None,
    ) -> None:
        self._pc = pc
        self._reliable_dc = reliable_dc
        self._unreliable_dc = unreliable_dc
        self._loop = asyncio.get_event_loop()

        self._packets: asyncio.Queue[bytes] = asyncio.Queue()
        self._recv_buf = bytearray()
        self._expected_remaining: int | None = None
        self._closed = False

        # Register callbacks.
        self._reliable_dc.on_message(self._on_message_cb)
        self._reliable_dc.on_closed(self._on_dc_close_cb)
        self._reliable_dc.on_error(lambda e: logger.error("reliable DC error: %s", e))

        # Monitor PeerConnection state.
        self._pc.on_state_change(self._on_pc_state_cb)
        self._pc.on_ice_state_change(self._on_ice_state_cb)

    def _on_pc_state_cb(self, state: dc.PeerConnection.State) -> None:
        logger.info("PC state: %s", state)

    def _on_ice_state_cb(self, state: dc.PeerConnection.IceState) -> None:
        logger.info("PC ICE state: %s", state)

    def _on_dc_close_cb(self) -> None:
        """Handle reliable DataChannel close (called from libdatachannel thread)."""
        logger.warning("reliable DC closed")
        self._closed = True
        try:
            self._loop.call_soon_threadsafe(self._packets.put_nowait, b"")
        except Exception:
            pass

    def _on_message_cb(self, msg: dc.Message) -> None:
        """Handle incoming DataChannel message (called from libdatachannel thread)."""
        data = bytes(msg)
        logger.debug("DC recv: %d bytes, hex=%s", len(data), data[:80].hex())
        if len(data) < 2:
            logger.warning("received segment too short: %d bytes", len(data))
            return

        remaining = data[0]
        payload = data[1:]

        if self._expected_remaining is not None:
            if remaining != self._expected_remaining - 1:
                logger.warning(
                    "segment ordering error: expected remaining=%d, got=%d",
                    self._expected_remaining - 1, remaining,
                )
                self._recv_buf.clear()
                self._expected_remaining = None
                return

        self._expected_remaining = remaining
        self._recv_buf.extend(payload)

        if remaining == 0:
            packet = bytes(self._recv_buf)
            self._recv_buf.clear()
            self._expected_remaining = None
            try:
                self._loop.call_soon_threadsafe(self._packets.put_nowait, packet)
            except asyncio.QueueFull:
                logger.warning("packet queue full, dropping packet")

    async def read_packet(self) -> bytes:
        data = await self._packets.get()
        if not data and self._closed:
            raise ConnectionError("DataChannel closed by remote")
        return data

    async def write_packet(self, data: bytes) -> None:
        if self._closed:
            raise ConnectionError("connection is closed")

        total_segments = max(1, (len(data) + MAX_MESSAGE_SIZE - 1) // MAX_MESSAGE_SIZE)
        if total_segments > MAX_SEGMENTS:
            raise ValueError(f"data too large: {len(data)} bytes")

        remaining = total_segments - 1
        offset = 0
        while offset < len(data):
            end = min(offset + MAX_MESSAGE_SIZE, len(data))
            segment = bytes([remaining]) + data[offset:end]
            logger.debug("DC send: %d bytes, hex=%s", len(segment), segment[:80].hex())
            self._reliable_dc.send(segment)
            offset = end
            remaining -= 1

        if len(data) == 0:
            self._reliable_dc.send(bytes([0]))

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._reliable_dc.close()
            if self._unreliable_dc:
                self._unreliable_dc.close()
            self._pc.close()
        except Exception as e:
            logger.debug("error closing connection: %s", e)

    def batch_header(self) -> bytes | None:
        return None

    def disable_encryption(self) -> bool:
        return True


class LdcNetherNetNetwork(Network):
    """NetherNet using libdatachannel (native C++ WebRTC).

    Drop-in replacement for NetherNetNetwork (aiortc-based).
    """

    def __init__(self, mc_token: str, network_id: str = "", signaling_url: str = "", use_jsonrpc: bool = False) -> None:
        self._mc_token = mc_token
        self._network_id = network_id or generate_network_id()
        self._signaling_url = signaling_url
        self._use_jsonrpc = use_jsonrpc

    async def connect(self, address: str) -> NetworkConnection:
        if address.startswith("nethernet:"):
            address = address[len("nethernet:"):]
        logger.info("connecting to NetherNet peer: %s (libdatachannel)", address)

        max_retries = 5
        for attempt in range(max_retries):
            try:
                return await self._try_connect(address)
            except ConnectionError as e:
                if "Player not found" in str(e) and attempt < max_retries - 1:
                    wait = 3 * (attempt + 1)
                    logger.info("peer not found (attempt %d/%d), retrying in %ds...",
                                attempt + 1, max_retries, wait)
                    await asyncio.sleep(wait)
                    continue
                raise
        raise ConnectionError("failed to connect after retries")

    async def _try_connect(self, address: str) -> NetworkConnection:
        kwargs = {}
        if self._signaling_url:
            kwargs["signaling_url"] = self._signaling_url
        if self._use_jsonrpc:
            signaling = JsonRpcSignaling(**kwargs)
        else:
            signaling = WebSocketSignaling(**kwargs)
        await signaling.connect(self._network_id, self._mc_token)

        try:
            # Get TURN/STUN credentials.
            creds = await signaling.credentials(timeout=10.0)
            logger.debug("received %d ICE servers", len(creds.ice_servers))

            # Build configuration.
            config = dc.Configuration()
            ice_servers = []
            for server in creds.ice_servers:
                logger.debug("ICE server: urls=%s", server.urls)
                for url in server.urls:
                    s = dc.IceServer(url)
                    s.username = server.username or ""
                    s.password = server.password or ""
                    ice_servers.append(s)
            config.ice_servers = ice_servers
            config.disable_auto_negotiation = True

            # Create PeerConnection.
            pc = dc.PeerConnection(config)
            loop = asyncio.get_event_loop()
            connection_id = random.getrandbits(64)

            # Events for async coordination.
            gathering_done = asyncio.Event()
            connected = asyncio.Event()
            reliable_open = asyncio.Event()
            local_desc_ready = asyncio.Event()
            local_sdp = {}
            local_candidates = []

            def on_gathering_state(state):
                logger.info("gathering state: %s", state)
                if state == dc.PeerConnection.GatheringState.Complete:
                    loop.call_soon_threadsafe(gathering_done.set)

            def on_state(state):
                logger.info("PC state: %s", state)
                if state == dc.PeerConnection.State.Connected:
                    loop.call_soon_threadsafe(connected.set)

            def on_local_desc(desc):
                local_sdp['sdp'] = str(desc)
                local_sdp['type'] = desc.type_string()
                logger.info("local description ready (type=%s)", desc.type_string())
                loop.call_soon_threadsafe(local_desc_ready.set)

            def on_local_candidate(candidate):
                logger.debug("local candidate: %s", candidate.candidate())
                local_candidates.append(candidate)

            pc.on_gathering_state_change(on_gathering_state)
            pc.on_state_change(on_state)
            pc.on_local_description(on_local_desc)
            pc.on_local_candidate(on_local_candidate)

            # Create data channels.
            reliable_init = dc.DataChannelInit()
            reliable_dc = pc.create_data_channel("ReliableDataChannel", reliable_init)

            unreliable_init = dc.DataChannelInit()
            unreliable_rel = dc.Reliability()
            unreliable_rel.unordered = True
            unreliable_rel.max_retransmits = 0
            unreliable_init.reliability = unreliable_rel
            unreliable_dc = pc.create_data_channel("UnreliableDataChannel", unreliable_init)

            def on_reliable_open():
                logger.info("reliable DC opened")
                loop.call_soon_threadsafe(reliable_open.set)

            reliable_dc.on_open(on_reliable_open)

            # Set local description to trigger SDP generation.
            pc.set_local_description(dc.Description.Type.Offer)

            # Wait for local description.
            await asyncio.wait_for(local_desc_ready.wait(), timeout=5.0)

            # Wait for ICE gathering to complete.
            await asyncio.wait_for(gathering_done.wait(), timeout=10.0)

            # Re-read local description (includes candidates after gathering).
            final_desc = pc.local_description()
            sdp_text = str(final_desc) if final_desc else local_sdp.get('sdp', '')
            logger.info("SDP offer:\n%s", sdp_text)

            # Send offer via signaling.
            await signaling.signal(Signal(
                type=SIGNAL_OFFER,
                connection_id=connection_id,
                data=sdp_text,
                network_id=address,
            ))

            # Wait for answer.
            conn = LdcNetherNetConn(pc, reliable_dc, unreliable_dc)
            answer_received = False

            while not answer_received:
                sig = await signaling.receive(timeout=30.0)
                if sig.connection_id != connection_id:
                    continue

                if sig.type == SIGNAL_ANSWER:
                    logger.info("SDP answer:\n%s", sig.data)
                    answer_desc = dc.Description(sig.data, "answer")
                    pc.set_remote_description(answer_desc)
                    answer_received = True
                    logger.info("received SDP answer from %s", sig.network_id)

                elif sig.type == SIGNAL_CANDIDATE:
                    candidate_str = sig.data.strip()
                    if candidate_str.startswith("a="):
                        candidate_str = candidate_str[2:]
                    try:
                        cand = dc.Candidate(candidate_str, "0")
                        pc.add_remote_candidate(cand)
                        logger.debug("added remote candidate: %s", candidate_str[:80])
                    except Exception as e:
                        logger.debug("failed to add remote candidate: %s", e)

                elif sig.type == SIGNAL_ERROR:
                    raise ConnectionError(f"remote error (code: {sig.data})")

            # Handle post-answer signals in background.
            asyncio.create_task(
                _handle_post_answer_signals(signaling, pc, connection_id, conn)
            )

            # Wait for reliable DataChannel to open.
            await asyncio.wait_for(reliable_open.wait(), timeout=30.0)
            logger.info("NetherNet connection established to %s", address)

            return conn

        except Exception:
            await signaling.close()
            raise

    async def ping(self, address: str) -> bytes:
        raise NotImplementedError("NetherNet does not support ping")

    async def listen(self, address: str):
        raise NotImplementedError("NetherNet listen not implemented")


async def _handle_post_answer_signals(
    signaling: WebSocketSignaling | JsonRpcSignaling,
    pc: dc.PeerConnection,
    connection_id: int,
    conn: LdcNetherNetConn,
) -> None:
    """Background task: handle signals received after the SDP answer."""
    try:
        while True:
            try:
                sig = await signaling.receive(timeout=60.0)
            except asyncio.TimeoutError:
                continue

            if sig.connection_id != connection_id:
                continue

            if sig.type == SIGNAL_CANDIDATE:
                candidate_str = sig.data.strip()
                if candidate_str.startswith("a="):
                    candidate_str = candidate_str[2:]
                try:
                    cand = dc.Candidate(candidate_str, "0")
                    pc.add_remote_candidate(cand)
                except Exception:
                    pass
            elif sig.type == SIGNAL_ERROR:
                logger.warning("remote error signal: code=%s", sig.data)
                await conn.close()
                break
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.debug("post-answer signal handler ended: %s", e)
    finally:
        await signaling.close()
