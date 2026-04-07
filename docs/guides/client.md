# クライアント接続ガイド

## BDS (ローカルサーバー) への接続

BDS (Bedrock Dedicated Server) に接続するには、`RakNetNetwork` を Dialer に渡します。

```python
import asyncio
from mcbe.dial import Dialer
from mcbe.raknet import RakNetNetwork
from mcbe.proto.login.data import IdentityData

async def main():
    dialer = Dialer(
        identity_data=IdentityData(display_name="Steve"),
        network=RakNetNetwork(),
    )
    async with await dialer.dial("127.0.0.1:19132") as conn:
        print("Connected!")
        while not conn.closed:
            pk = await conn.read_packet()
            print(f"Received: {type(pk).__name__}")

asyncio.run(main())
```

`Dialer.dial()` は以下を自動的に処理します:

1. RakNet トランスポート接続 (MTU ネゴシエーション)
2. RequestNetworkSettings / NetworkSettings (圧縮設定)
3. Login (自己署名 JWT)
4. リソースパックネゴシエーション
5. スポーン待機

返される `Connection` はすぐにパケットの読み書きが可能です。

## LAN ワールドへの接続

LAN 上で「マルチプレイヤーに公開」されているワールドに接続する場合も同じ手順です。接続先をホストデバイスのローカル IP アドレスに変更します。

```python
import asyncio
from mcbe.dial import Dialer
from mcbe.raknet import RakNetNetwork
from mcbe.proto.login.data import IdentityData

async def main():
    # 1. RakNet で Ping して存在確認 (任意)
    network = RakNetNetwork()
    try:
        pong = await network.ping("192.168.1.10:19132")
        print(f"Server found: {pong.decode()}")
    except Exception as e:
        print(f"Server not responding: {e}")
        return

    # 2. RakNetNetwork を指定して接続
    dialer = Dialer(
        identity_data=IdentityData(display_name="mcbe_player"),
        network=network,
    )
    async with await dialer.dial("192.168.1.10:19132") as conn:
        print("Connected to LAN world!")
        while not conn.closed:
            pk = await conn.read_packet()
            print(f"Received: {type(pk).__name__}")

asyncio.run(main())
```

### 接続先アドレスの確認方法

- ワールドを開いているデバイスの **ローカル IP アドレス** (例: `192.168.1.10`) を使用
- ポートはデフォルト `19132`。Minecraft の設定画面で確認可能
- ワールド側で **設定 → マルチプレイヤー → 「LAN プレイヤーに表示」** を有効にする

### 注意事項

- LAN ワールドは認証なし (オフラインモード) で接続可能。Dialer はデフォルトで自己署名 JWT を生成する
- Xbox Live 認証が必要なサーバーに接続する場合は、`auth/` モジュールで取得したトークンを設定する

## パケットの読み取りループ

`Connection.read_packet()` は次のパケットが届くまでブロックします。タイムアウトを設定するには `asyncio.wait_for()` を使います。

```python
from mcbe.proto.pool import UnknownPacket

async with await dialer.dial(address) as conn:
    while not conn.closed:
        try:
            pk = await asyncio.wait_for(conn.read_packet(), timeout=30.0)
            name = type(pk).__name__
            if isinstance(pk, UnknownPacket):
                name = f"Unknown(0x{pk.packet_id:02x}, {len(pk.payload)} bytes)"
            print(f"Received: {name}")
        except asyncio.TimeoutError:
            print("No packets for 30s, disconnecting")
            break
```

## 参考

- `examples/client.py` --- BDS 接続サンプル
- `examples/lan_connect.py` --- LAN ワールド接続サンプル
