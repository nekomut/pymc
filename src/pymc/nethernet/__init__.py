"""NetherNet protocol implementation for Minecraft Bedrock Edition.

Provides WebRTC-based networking used by Realms (NETHERNET_JSONRPC protocol).

Two backends are supported:
- **libdatachannel** (C++ native, via usrsctp/OpenSSL) — preferred if installed
- **aiortc** (pure Python) — included as base dependency, patched for BDS compatibility

Use :func:`create_network` to get the best available backend automatically.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def create_network(
    *,
    mc_token: str,
    signaling_url: str = "",
    use_jsonrpc: bool = False,
    backend: str | None = None,
):
    """Create a NetherNet Network using the best available backend.

    Args:
        mc_token: MCToken authorization header value.
        signaling_url: WebSocket signaling server URL.
        use_jsonrpc: Use JSON-RPC signaling (for NETHERNET_JSONRPC).
        backend: Force a specific backend ("libdatachannel" or "aiortc").
            If None, libdatachannel is preferred when available.

    Returns:
        A Network instance (LdcNetherNetNetwork or NetherNetNetwork).

    Raises:
        ImportError: If the requested backend is not installed.
    """
    if backend == "libdatachannel":
        return _create_ldc(mc_token, signaling_url, use_jsonrpc)
    if backend == "aiortc":
        return _create_aiortc(mc_token, signaling_url, use_jsonrpc)
    if backend is not None:
        raise ValueError(f"unknown backend: {backend!r} (use 'libdatachannel' or 'aiortc')")

    # Auto-detect: prefer libdatachannel if available.
    try:
        return _create_ldc(mc_token, signaling_url, use_jsonrpc)
    except ImportError:
        pass

    return _create_aiortc(mc_token, signaling_url, use_jsonrpc)


def _create_ldc(mc_token, signaling_url, use_jsonrpc):
    from pymc.nethernet.ldc_network import LdcNetherNetNetwork

    logger.info("NetherNet backend: libdatachannel")
    return LdcNetherNetNetwork(
        mc_token=mc_token,
        signaling_url=signaling_url,
        use_jsonrpc=use_jsonrpc,
    )


def _create_aiortc(mc_token, signaling_url, use_jsonrpc):
    from pymc.nethernet.network import NetherNetNetwork

    logger.info("NetherNet backend: aiortc")
    return NetherNetNetwork(
        mc_token=mc_token,
        signaling_url=signaling_url,
        use_jsonrpc=use_jsonrpc,
    )
