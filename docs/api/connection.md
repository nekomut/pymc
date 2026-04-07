# Connection クラス

`mcbe.conn` モジュールは、Minecraft Bedrock Edition プロトコルのパケットレベル通信を管理する `Connection` クラスを提供する。

## 定数

### `DEFAULT_FLUSH_RATE`

```python
DEFAULT_FLUSH_RATE = 0.05
```

デフォルトのフラッシュ間隔（秒）。Go 実装の 50ms に合わせている。

---

## Connection クラス

パケットの読み書き、バッファリング、圧縮、暗号化を処理する接続クラス。

### コンストラクタ

```python
Connection(
    transport: Transport,
    pool: PacketPool,
    *,
    flush_rate: float = DEFAULT_FLUSH_RATE,
    use_batch_header: bool = True,
    disable_encryption: bool = False,
)
```

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `transport` | `Transport` | (必須) | 下位トランスポート（RakNet、TCP など） |
| `pool` | `PacketPool` | (必須) | パケット ID → クラスのマッピング（`server_pool()` or `client_pool()`） |
| `flush_rate` | `float` | `0.05` | 自動フラッシュ間隔（秒）。`0` 以下で自動フラッシュ無効 |
| `use_batch_header` | `bool` | `True` | バッチヘッダー (0xFE) を使用するか。NetherNet では `False` |
| `disable_encryption` | `bool` | `False` | 暗号化を無効化するか。NetherNet では `True`（DTLS が担当） |

---

## メソッド

### 書き込み

#### `write_packet(pk: Packet) -> None`

```python
async def write_packet(pk: Packet) -> None
```

パケットをバッファに追加する。自動フラッシュタスクか、`flush()` の明示的呼び出しで送信される。

#### `write_packet_immediate(pk: Packet) -> None`

```python
async def write_packet_immediate(pk: Packet) -> None
```

パケットをバッファリングせず即座に送信する。ハンドシェイクの最初のパケット（RequestNetworkSettings など）で使用される。

#### `flush() -> None`

```python
async def flush() -> None
```

バッファ内のすべてのパケットを単一バッチとして送信する。バッファが空の場合は何もしない。

### 読み込み

#### `read_packet() -> Packet`

```python
async def read_packet() -> Packet
```

次のパケットを読み取る。パケットが利用可能になるまでブロックする。接続が閉じられた場合は `ConnectionError` を送出する。

#### `read_packet_nowait() -> Packet | None`

```python
def read_packet_nowait() -> Packet | None
```

パケットが利用可能であれば即座に返す。なければ `None` を返す。同期メソッド。

### 圧縮・暗号化

#### `enable_compression(algorithm, threshold)`

```python
def enable_compression(
    algorithm: int = COMPRESSION_FLATE,
    threshold: int = 256,
) -> None
```

パケット圧縮を有効にする。以降のバッチはこの設定で圧縮される。

| パラメータ | 説明 |
|---|---|
| `algorithm` | `COMPRESSION_FLATE` (0x00) / `COMPRESSION_SNAPPY` (0x01) |
| `threshold` | 圧縮を適用する最小バイト数（デフォルト: 256） |

#### `enable_encryption(key)`

```python
def enable_encryption(key: bytes) -> None
```

AES-256-CTR 暗号化を有効にする。`key` は 32 バイトの鍵。`disable_encryption=True` の場合は何もしない。

### ライフサイクル

#### `start()`

```python
async def start() -> None
```

バックグラウンドのフラッシュタスクと読み取りタスクを開始する。

#### `close()`

```python
async def close() -> None
```

残りのパケットをフラッシュし、バックグラウンドタスクをキャンセルし、トランスポートを閉じる。

#### `closed` プロパティ

```python
@property
def closed(self) -> bool
```

接続が閉じられているかどうかを返す。

---

## コンテキストマネージャ

`Connection` は `async with` で使用できる。`__aenter__` で `start()` が呼ばれ、`__aexit__` で `close()` が呼ばれる。

```python
async with Connection(transport, pool) as conn:
    await conn.write_packet(some_packet)
    await conn.flush()
    pk = await conn.read_packet()
```

---

## 内部動作

- **バッファリング**: `write_packet()` はパケットをバッファに追加し、バックグラウンドタスクが `flush_rate` 間隔でフラッシュする
- **バッチ処理**: フラッシュ時、バッファ内のすべてのパケットは単一バッチにまとめられる
- **圧縮**: バッチ全体に対して適用される（flate or snappy）
- **暗号化**: 圧縮後のバッチに対して AES-256-CTR + SHA-256 チェックサムが適用される
- **受信キュー**: 最大 128 パケットのキューで受信パケットをバッファリングする
