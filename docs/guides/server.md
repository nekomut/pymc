# サーバー構築ガイド

## ListenConfig

`ListenConfig` でサーバーの動作を設定します。

```python
from mcbe.listener import ListenConfig
from mcbe.proto.pool import COMPRESSION_FLATE

config = ListenConfig(
    max_players=20,                  # 最大プレイヤー数
    authentication_disabled=True,    # 認証を無効化 (自己署名JWTを受け入れる)
    compression=COMPRESSION_FLATE,   # 圧縮アルゴリズム (flate)
    compression_threshold=256,       # 圧縮閾値 (バイト)
    flush_rate=0.05,                 # パケットフラッシュ間隔 (秒)
    server_name="My Server",         # サーバー名
    game_version="1.21.50",          # ゲームバージョン
)
```

### パラメータ

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `max_players` | 20 | 最大接続プレイヤー数 |
| `authentication_disabled` | `True` | `True` で自己署名 JWT を受け入れる |
| `compression` | `COMPRESSION_FLATE` | 圧縮アルゴリズム |
| `compression_threshold` | 256 | この値以上のパケットを圧縮する |
| `flush_rate` | 0.05 | パケットバッファのフラッシュ間隔 (秒) |
| `server_name` | `"mcbe Server"` | Ping 応答に表示されるサーバー名 |
| `game_version` | `"1.21.50"` | ゲームバージョン文字列 |

## listen() 関数

`listen()` でサーバーを起動します。

```python
from mcbe.listener import ListenConfig, listen

server = await listen(
    "0.0.0.0:19132",    # リッスンアドレス
    config=config,       # ListenConfig (省略可)
    network=network,     # Network トランスポート (省略可、デフォルトは TCPNetwork)
)
```

RakNet で実際の Minecraft クライアントからの接続を受け付けるには:

```python
from mcbe.raknet import RakNetNetwork

server = await listen(
    "0.0.0.0:19132",
    config=config,
    network=RakNetNetwork(),
)
```

## 接続の受け入れ

`Listener.accept()` はハンドシェイク完了済みの `Connection` を返します。内部では以下が自動処理されます:

1. RequestNetworkSettings 受信 → NetworkSettings 送信
2. Login 受信 → JWT 検証
3. 暗号化ハンドシェイク (認証時)
4. PlayStatus (LoginSuccess) 送信
5. リソースパックネゴシエーション

```python
conn = await server.accept()
print(f"Player connected!")
```

## パケットの読み書き

```python
# パケット受信
pk = await conn.read_packet()

# パケット送信
await conn.write_packet(some_packet)
await conn.flush()

# 即時送信 (バッファリングなし)
await conn.write_packet_immediate(some_packet)
```

## 完全なサンプル

```python
import asyncio
from mcbe.listener import ListenConfig, listen

async def main():
    config = ListenConfig(
        server_name="My Server",
        authentication_disabled=True,
    )
    server = await listen("0.0.0.0:19132", config=config)
    print("Listening on 0.0.0.0:19132...")

    try:
        while True:
            conn = await server.accept()
            print("Player connected!")
            asyncio.create_task(handle_player(conn))
    finally:
        await server.close()

async def handle_player(conn):
    try:
        while not conn.closed:
            pk = await conn.read_packet()
            print(f"Received: {type(pk).__name__}")
    except Exception as e:
        print(f"Player disconnected: {e}")
    finally:
        await conn.close()

asyncio.run(main())
```

## 参考

- `src/mcbe/listener.py` --- Listener / ListenConfig の実装
