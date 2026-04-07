# Dialer クラス

`mcbe.dial` モジュールは、Minecraft Bedrock Edition サーバーへのクライアント接続を担当する。

## 定数

### `PROTOCOL_VERSION`

```python
PROTOCOL_VERSION = 944
```

現在のプロトコルバージョン。サーバーとのハンドシェイク時にこの値がネゴシエーションされる。

---

## Dialer クラス

サーバーへ接続し、ログインハンドシェイクを完了して `Connection` を返すクラス。

### コンストラクタ

```python
Dialer(
    *,
    identity_data: IdentityData | None = None,
    client_data: ClientData | None = None,
    protocol_version: int = PROTOCOL_VERSION,
    flush_rate: float = 0.05,
    chunk_radius: int = 16,
    network: Network | None = None,
    legacy_login: bool = False,
    login_chain: str | None = None,
    auth_key: ec.EllipticCurvePrivateKey | None = None,
    multiplayer_token: str = "",
)
```

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `identity_data` | `IdentityData \| None` | `None` | プレイヤーの識別情報（表示名、UUID、XUID）。`None` の場合は "Steve" という名前で生成される |
| `client_data` | `ClientData \| None` | `None` | クライアントのデバイス・スキンデータ。`None` の場合はデフォルト値が使用される |
| `protocol_version` | `int` | `944` | ネゴシエーションするプロトコルバージョン |
| `flush_rate` | `float` | `0.05` | パケットフラッシュ間隔（秒） |
| `chunk_radius` | `int` | `16` | リクエストするチャンク描画距離 |
| `network` | `Network \| None` | `None` | ネットワークトランスポート。`None` の場合は `TCPNetwork` が使用される |
| `legacy_login` | `bool` | `False` | レガシーログイン方式を使用するか |
| `login_chain` | `str \| None` | `None` | 認証済み JWT チェーン文字列。指定時はオンライン認証モードで接続する |
| `auth_key` | `ec.EllipticCurvePrivateKey \| None` | `None` | 認証用 ECDSA P-384 秘密鍵。`login_chain` 取得時に使用した鍵と一致させる必要がある |
| `multiplayer_token` | `str` | `""` | マルチプレイヤートークン（OIDC ベース認証用） |

### メソッド

#### `dial(address: str) -> Connection`

```python
async def dial(address: str) -> Connection
```

サーバーに接続し、ログインハンドシェイクを完了する。

- **引数**: `address` — `"host:port"` 形式のサーバーアドレス
- **戻り値**: ゲームプレイパケットの送受信が可能な `Connection`
- **例外**: ハンドシェイク中にエラーが発生した場合、接続は自動的に閉じられる

---

## 内部ハンドシェイクフロー

`dial()` は以下の手順でサーバーとの接続を確立する:

1. **RequestNetworkSettings** 送信 — プロトコルバージョンを通知
2. **NetworkSettings** 受信 — 圧縮設定を適用
3. **Login** 送信 — 認証情報を含む接続リクエスト（オフライン or 認証済み JWT）
4. **ServerToClientHandshake** / **PlayStatus** 受信 — 暗号化の有効化（ECDH 鍵交換）
5. **ClientToServerHandshake** 送信 → **PlayStatus (LoginSuccess)** 待機
6. **ResourcePacksInfo** / **ResourcePackStack** の交換
7. **PlayStatus (PlayerSpawn)** まで待機 — チャンク半径をリクエスト

NetherNet (WebRTC) トランスポートの場合、バッチヘッダーと Minecraft レイヤーの暗号化はスキップされる（DTLS が暗号化を担当するため）。

---

## コード例

```python
import asyncio
from mcbe.dial import Dialer
from mcbe.raknet.network import RakNetNetwork

async def main():
    dialer = Dialer(
        network=RakNetNetwork(),
        chunk_radius=8,
    )
    conn = await dialer.dial("127.0.0.1:19132")

    try:
        while True:
            pk = await conn.read_packet()
            print(f"受信: {type(pk).__name__} (id={pk.packet_id})")
    finally:
        await conn.close()

asyncio.run(main())
```

### 認証済みログインの例

```python
from mcbe.auth.live import get_live_token
from mcbe.auth.xbox import request_xbl_token
from mcbe.auth.minecraft import request_minecraft_chain
from cryptography.hazmat.primitives.asymmetric import ec

async def authenticated_login():
    # 1. Microsoft Live トークン取得
    live_token = await get_live_token()

    # 2. Xbox Live トークン取得
    xbl_token = await request_xbl_token(
        live_token, "https://multiplayer.minecraft.net/"
    )

    # 3. Minecraft JWT チェーン取得
    auth_key = ec.generate_private_key(ec.SECP384R1())
    chain = await request_minecraft_chain(xbl_token, auth_key)

    # 4. 接続
    dialer = Dialer(
        login_chain=chain,
        auth_key=auth_key,
        network=RakNetNetwork(),
    )
    conn = await dialer.dial("server.example.com:19132")
    return conn
```
