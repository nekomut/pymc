"""指定座標のブロック情報を取得するサンプル.

Usage:
    # BDS に接続して (0, 30, 0) のブロックを取得
    python examples/get_block.py

    # 座標を指定
    python examples/get_block.py --x 10 --y 64 --z 20

    # Realms に接続
    python examples/get_block.py --realms
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import uuid

from cryptography.hazmat.primitives.asymmetric import ec

from mcbe.dial import Dialer
from mcbe.proto.login.data import IdentityData
from mcbe.proto.packet.command_output import CommandOutput
from mcbe.proto.packet.command_request import CommandOrigin, CommandRequest, ORIGIN_AUTOMATION_PLAYER
from mcbe.proto.packet.packet_violation_warning import PacketViolationWarning
from mcbe.raknet import RakNetNetwork

logger = logging.getLogger(__name__)


class _ColorFormatter(logging.Formatter):
    """ANSI カラー付きログフォーマッタ."""

    _COLORS = {
        logging.DEBUG: "\033[32m",    # 緑
        logging.WARNING: "\033[33m",  # 黄
        logging.ERROR: "\033[31m",    # 赤
        logging.CRITICAL: "\033[31m", # 赤
    }
    _RESET = "\033[0m"

    def format(self, record):
        msg = super().format(record)
        color = self._COLORS.get(record.levelno)
        if color:
            return f"{color}{msg}{self._RESET}"
        return msg


def _setup_logging(level: int) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_ColorFormatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logging.root.addHandler(handler)
    logging.root.setLevel(level)
    logging.getLogger(__name__).setLevel(min(level, logging.INFO))


async def resolve_realms(invite_code: str | None = None, backend: str | None = None):
    """Realms に認証して接続情報を返す."""
    from mcbe.auth.live import get_live_token, load_token
    from mcbe.auth.xbox import request_xbl_token
    from mcbe.auth.minecraft import request_minecraft_chain

    cached = load_token()
    live_token = await get_live_token()
    if cached and cached.valid():
        logger.info("キャッシュ済みトークンを使用")
    elif cached:
        logger.info("トークンを更新しました")
    else:
        logger.info("新規認証完了")

    # Realms API
    from mcbe.realms import RealmsClient
    xbl_realms = await request_xbl_token(live_token, "https://pocket.realms.minecraft.net/")
    async with RealmsClient(xbl_realms) as client:
        if invite_code:
            realm = await client.realm(invite_code)
        else:
            realms = await client.realms()
            if not realms:
                raise RuntimeError("アクセス可能な Realm がありません")
            realm = realms[0]
        logger.info("Realm: %s (%s)", realm.name, realm.state)
        realm_addr = await realm.address()

    address = realm_addr.address
    is_nethernet = realm_addr.network_protocol and "NETHERNET" in realm_addr.network_protocol.upper()
    is_jsonrpc = is_nethernet and "JSONRPC" in realm_addr.network_protocol.upper()

    key = ec.generate_private_key(ec.SECP384R1())
    network = None
    multiplayer_token = ""

    if is_nethernet:
        from mcbe.auth.service import discover, request_service_token, request_multiplayer_token
        from mcbe.auth.playfab import login_with_xbox as playfab_login
        from mcbe.nethernet import create_network

        xbl_pf = await request_xbl_token(live_token, "http://playfab.xboxlive.com/")
        discovery = await discover()
        playfab_ticket = await playfab_login(xbl_pf, title_id=discovery.playfab_title_id)
        service_token = await request_service_token(
            discovery.auth_uri, xbl_pf.auth_header_value(),
            playfab_title_id=discovery.playfab_title_id,
            playfab_session_ticket=playfab_ticket,
        )
        multiplayer_token = await request_multiplayer_token(
            discovery.auth_uri, service_token, key.public_key(),
        )
        network = create_network(
            mc_token=service_token.authorization_header,
            signaling_url=discovery.signaling_info.service_uri,
            use_jsonrpc=is_jsonrpc,
            backend=backend,
        )
        backend_name = "libdatachannel" if "Ldc" in type(network).__name__ else "aiortc"
        logger.info("WebRTC バックエンド: %s", backend_name)

    xbl_mp = await request_xbl_token(live_token, "https://multiplayer.minecraft.net/")
    login_chain = await request_minecraft_chain(xbl_mp, key)

    logger.info("Realm アドレス: %s (プロトコル: %s)", address, realm_addr.network_protocol)
    return address, login_chain, key, multiplayer_token, network


async def main(
    address: str, x: int, y: int, z: int,
    realms: bool = False, invite_code: str | None = None,
    backend: str | None = None,
    log_level: str = "WARNING",
) -> None:
    _setup_logging(getattr(logging, log_level))

    login_chain = None
    auth_key = None
    multiplayer_token = ""
    network = None

    if realms:
        logger.info("Realms モード: 認証中...")
        address, login_chain, auth_key, multiplayer_token, network = await resolve_realms(invite_code, backend=backend)
    if network is None:
        network = RakNetNetwork()

    dialer = Dialer(
        identity_data=IdentityData(display_name="mcbe"),
        network=network,
        login_chain=login_chain,
        auth_key=auth_key,
        multiplayer_token=multiplayer_token,
    )

    async with await dialer.dial(address) as conn:
        logger.info("接続完了")

        cmd = f"/testforblock {x} {y} {z} air"
        request_id = str(uuid.uuid4())
        await conn.write_packet(CommandRequest(
            command_line=cmd,
            command_origin=CommandOrigin(origin=ORIGIN_AUTOMATION_PLAYER, request_id=request_id),
            internal=False,
        ))
        await conn.flush()
        logger.info("実行: %s", cmd)

        # CommandOutput を待つ
        found = False
        deadline = asyncio.get_event_loop().time() + 10.0
        while asyncio.get_event_loop().time() < deadline:
            try:
                pk = await asyncio.wait_for(conn.read_packet(), timeout=5.0)
            except (asyncio.TimeoutError, TimeoutError):
                break
            except ConnectionError:
                break
            logger.debug("recv: %s", type(pk).__name__)
            if isinstance(pk, PacketViolationWarning):
                logger.warning("PacketViolationWarning: type=%d severity=%d packet_id=%d context=%s",
                               pk.violation_type, pk.severity, pk.violating_packet_id, pk.violation_context)
            if isinstance(pk, CommandOutput):
                found = True
                for msg in pk.output_messages:
                    if msg.success:
                        logger.info("(%d, %d, %d): air", x, y, z)
                    else:
                        # params: ['x', 'y', 'z', '%tile.<block>.name', '%tile.air.name']
                        block_name = "unknown"
                        for p in msg.parameters:
                            if p.startswith("%tile.") and p != "%tile.air.name":
                                block_name = p.removeprefix("%tile.").removesuffix(".name")
                                break
                        logger.info("(%d, %d, %d): %s", x, y, z, block_name)
                    logger.debug("  message_id=%s params=%s", msg.message_id, msg.parameters)
                if pk.data_set:
                    logger.debug("data_set: %s", pk.data_set.strip())
                if not pk.output_messages and not pk.data_set:
                    logger.info("(%d, %d, %d): (応答なし)", x, y, z)
                break
        if not found:
            logger.info("CommandOutput を受信できませんでした (権限不足の可能性: /op が必要)")

    logger.info("完了")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="指定座標のブロック情報を取得する")
    parser.add_argument("--bds-address", default="127.0.0.1:19132", help="BDS サーバーアドレス (default: 127.0.0.1:19132)")
    parser.add_argument("--x", type=int, default=0, help="X 座標 (default: 0)")
    parser.add_argument("--y", type=int, default=30, help="Y 座標 (default: 30)")
    parser.add_argument("--z", type=int, default=0, help="Z 座標 (default: 0)")
    parser.add_argument("--realms", action="store_true", help="Realms に接続")
    parser.add_argument("--invite-code", help="Realm 招待コード")
    parser.add_argument("--backend", choices=["aiortc", "libdatachannel"], default=None, help="WebRTC バックエンド (default: libdatachannel 優先)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING"], default="WARNING", help="ログレベル (default: WARNING, __main__ は常に INFO)")
    args = parser.parse_args()
    asyncio.run(main(args.bds_address, args.x, args.y, args.z, realms=args.realms, invite_code=args.invite_code, backend=args.backend, log_level=args.log_level))
