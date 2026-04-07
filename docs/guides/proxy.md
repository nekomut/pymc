# MITM プロキシガイド

## 概要

MITM (Man-in-the-Middle) プロキシは、Minecraft クライアントとサーバーの間に入り、全パケットを中継しながらログに記録します。プロトコル解析やデバッグに便利です。

```
Minecraft Client → Proxy (port 19133) → BDS Server (port 19132)
```

プロキシはクライアントからの接続を Listener で受け入れ、Dialer でサーバーに接続し、双方向にパケットを転送します。

## 使い方

```bash
python examples/proxy.py --listen 0.0.0.0:19133 --remote 127.0.0.1:19132
```

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--listen` | `0.0.0.0:19133` | プロキシがリッスンするアドレス |
| `--remote` | `127.0.0.1:19132` | 転送先サーバーのアドレス |

Minecraft クライアントからプロキシのアドレス (例: `127.0.0.1:19133`) に接続すると、プロキシがサーバーに中継します。

## 出力例

```
2024-01-01 12:00:00 [INFO] proxy: Starting proxy: 0.0.0.0:19133 → 127.0.0.1:19132
2024-01-01 12:00:10 [INFO] proxy: New client connected, dialing remote 127.0.0.1:19132
2024-01-01 12:00:11 [INFO] proxy: Connected to remote server
2024-01-01 12:00:11 [INFO] proxy: [C→S] RequestChunkRadius
2024-01-01 12:00:11 [INFO] proxy: [S→C] ChunkRadiusUpdated
2024-01-01 12:00:11 [INFO] proxy: [S→C] PlayStatus
```

`[C→S]` はクライアントからサーバーへ、`[S→C]` はサーバーからクライアントへのパケットを示します。

## 参考

- `examples/proxy.py` --- プロキシの完全な実装
