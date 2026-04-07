# コマンド実行ガイド

## CommandRequest パケット

サーバー上でコマンドを実行するには `CommandRequest` パケットを送信します。

```python
from mcbe.proto.packet.command_request import CommandOrigin, CommandRequest, ORIGIN_PLAYER

await conn.write_packet(CommandRequest(
    command_line="/setblock 0 70 0 diamond_block",
    command_origin=CommandOrigin(origin=ORIGIN_PLAYER),
    internal=False,
    version="latest",
))
await conn.flush()
```

### 重要: version フィールド

**`version` フィールドは必ず `"latest"` を指定してください。**

空文字列 (`""`) を指定すると、Realms 接続時に `PacketViolationWarning` が発生します。BDS ではエラーにならないため気付きにくいですが、Realms では接続が不安定になる原因になります。

```python
# OK
CommandRequest(command_line="/say hello", ..., version="latest")

# NG - Realms で PacketViolationWarning が発生する
CommandRequest(command_line="/say hello", ..., version="")
```

### CommandOrigin

`CommandOrigin` にはコマンドの実行元を指定します。通常は `ORIGIN_PLAYER` を使用します。

```python
command_origin=CommandOrigin(origin=ORIGIN_PLAYER)
```

## コマンド実行例

`examples/place_block.py` より、ブロック配置の例:

```python
async with await dialer.dial(address) as conn:
    cmd = f"/setblock {x} {y} {z} {block}"
    await conn.write_packet(CommandRequest(
        command_line=cmd,
        command_origin=CommandOrigin(origin=ORIGIN_PLAYER),
        internal=False,
        version="latest",
    ))
    await conn.flush()

    # サーバーからの応答を少し待つ
    await asyncio.sleep(1.0)
```

## バッチコマンド実行パターン

大量のコマンドを連続実行する場合、`examples/terrain_build.py` のパターンが参考になります。

### NetworkStackLatency の処理

大量コマンド実行時は、サーバーから `NetworkStackLatency` パケットが送られてきます。`needs_response` が `True` の場合は応答を返す必要があります。応答しないと接続がタイムアウトします。

```python
from mcbe.proto.packet.network_stack_latency import NetworkStackLatency

async def read_packets(conn):
    """パケット読み取りタスク (バックグラウンド)."""
    try:
        while True:
            pk = await conn.read_packet()
            if isinstance(pk, NetworkStackLatency) and pk.needs_response:
                await conn.write_packet(
                    NetworkStackLatency(timestamp=pk.timestamp, needs_response=False)
                )
                await conn.flush()
    except Exception:
        pass

# バックグラウンドで読み取りタスクを起動
read_task = asyncio.create_task(read_packets(conn))
```

### コマンドの連続送信

コマンド間に短い `sleep` を挟むことで、サーバーへの負荷を分散します。

```python
async def run_cmd(conn, cmd: str):
    """コマンドを実行する."""
    await conn.write_packet(
        CommandRequest(
            command_line=cmd,
            command_origin=CommandOrigin(origin=ORIGIN_PLAYER),
            internal=False,
            version="latest",
        )
    )
    await conn.flush()
    await asyncio.sleep(0.01)  # サーバーへの負荷軽減

# 使用例: 大量のブロックを配置
for x in range(100):
    for z in range(100):
        await run_cmd(conn, f"/setblock {x} 64 {z} stone")
```

## 参考

- `examples/place_block.py` --- 単一ブロック配置
- `examples/terrain_build.py` --- 大量ブロック配置 (複数ボット並列)
