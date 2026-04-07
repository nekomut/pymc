"""Monkey-patches for aiortc to improve compatibility with Minecraft BDS.

Patches applied:
1. Reduce SCTP stream counts from 65535 to 1024 (matches libwebrtc default).
2. Add detailed SCTP chunk logging for diagnostics.
3. Log DTLS role and SCTP INIT parameters.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_patched = False


def apply():
    """Apply all aiortc patches. Safe to call multiple times."""
    global _patched
    if _patched:
        return
    _patched = True

    import aiortc.rtcsctptransport as sctp

    # 1. Reduce stream counts to match libwebrtc defaults.
    old_max = sctp.MAX_STREAMS
    sctp.MAX_STREAMS = 1024
    logger.info("aiortc patch: MAX_STREAMS %d -> %d", old_max, sctp.MAX_STREAMS)

    # 2. Wrap _init to log SCTP INIT parameters and DTLS role.
    _original_init = sctp.RTCSctpTransport._init

    async def _patched_init(self):
        # Log DTLS role.
        role = getattr(self.transport, "_role", None)
        ice_role = getattr(self.transport.transport, "role", None)
        logger.info(
            "SCTP _init: dtls_role=%s ice_role=%s is_server=%s port=%d",
            role, ice_role, self.is_server, self._local_port,
        )
        logger.info(
            "SCTP _init: outbound_streams=%d inbound_streams_max=%d rwnd=%d",
            self._outbound_streams_count,
            self._inbound_streams_max,
            self._advertised_rwnd,
        )
        await _original_init(self)

    sctp.RTCSctpTransport._init = _patched_init

    # 3. Wrap _receive_chunk to log all chunk types (not just ABORT).
    _original_receive_chunk = sctp.RTCSctpTransport._receive_chunk

    async def _patched_receive_chunk(self, chunk):
        chunk_name = type(chunk).__name__
        extra = ""
        if isinstance(chunk, sctp.InitChunk) or isinstance(chunk, sctp.InitAckChunk):
            extra = (
                f" tag={chunk.initiate_tag} rwnd={chunk.advertised_rwnd}"
                f" os={chunk.outbound_streams} mis={chunk.inbound_streams}"
                f" tsn={chunk.initial_tsn}"
            )
            if chunk.params:
                extra += f" params={[(t, v.hex()) for t, v in chunk.params]}"
        elif isinstance(chunk, sctp.AbortChunk):
            extra = f" params={chunk.params}"
        elif isinstance(chunk, sctp.SackChunk):
            extra = (
                f" cumtsn={chunk.cumulative_tsn} rwnd={chunk.advertised_rwnd}"
                f" gaps={len(chunk.gaps)} dups={len(chunk.duplicates)}"
            )
        elif isinstance(chunk, sctp.ForwardTsnChunk):
            extra = f" tsn={getattr(chunk, 'cumulative_tsn', '?')}"

        logger.debug("SCTP recv chunk: %s%s", chunk_name, extra)
        await _original_receive_chunk(self, chunk)

    sctp.RTCSctpTransport._receive_chunk = _patched_receive_chunk

    # 4. Wrap _send_chunk to log outbound chunks.
    _original_send_chunk = sctp.RTCSctpTransport._send_chunk

    async def _patched_send_chunk(self, chunk):
        chunk_name = type(chunk).__name__
        extra = ""
        if isinstance(chunk, sctp.InitChunk) or isinstance(chunk, sctp.InitAckChunk):
            extra = (
                f" tag={chunk.initiate_tag} rwnd={chunk.advertised_rwnd}"
                f" os={chunk.outbound_streams} mis={chunk.inbound_streams}"
                f" tsn={chunk.initial_tsn}"
            )
        elif isinstance(chunk, sctp.SackChunk):
            extra = f" cumtsn={chunk.cumulative_tsn} rwnd={chunk.advertised_rwnd}"

        logger.debug("SCTP send chunk: %s%s", chunk_name, extra)
        await _original_send_chunk(self, chunk)

    sctp.RTCSctpTransport._send_chunk = _patched_send_chunk

    # 5. Also patch the __init__ to apply reduced stream counts to new instances.
    _original_transport_init = sctp.RTCSctpTransport.__init__

    def _patched_transport_init(self, transport, port=5000):
        _original_transport_init(self, transport, port)
        # Override with patched values (the constructor reads MAX_STREAMS
        # at module level, but it was already changed above).
        self._inbound_streams_max = sctp.MAX_STREAMS
        self._outbound_streams_count = sctp.MAX_STREAMS
        logger.info(
            "SCTP transport created: port=%d streams=%d rwnd=%d",
            port, sctp.MAX_STREAMS, self._advertised_rwnd,
        )

    sctp.RTCSctpTransport.__init__ = _patched_transport_init

    logger.info("aiortc SCTP patches applied")
