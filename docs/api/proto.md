# プロトコル

`mcbe.proto` パッケージは、Minecraft Bedrock Edition プロトコルのバイナリ I/O、パケット基底クラス、パケット登録、バッチ処理、暗号化、型定義を提供する。

---

## PacketReader

`mcbe.proto.io.PacketReader` — バイナリデータをプロトコル形式で読み取るリーダー。

### コンストラクタ

```python
PacketReader(data: bytes | bytearray | BytesIO)
```

### プロパティ

| プロパティ | 型 | 説明 |
|---|---|---|
| `remaining` | `int` | 未読バイト数 |

### プリミティブ型

| メソッド | 戻り値 | 説明 |
|---|---|---|
| `uint8()` | `int` | 符号なし 8 ビット整数 |
| `int8()` | `int` | 符号付き 8 ビット整数 |
| `bool()` | `bool` | 真偽値（uint8 != 0） |
| `uint16()` | `int` | 符号なし 16 ビット整数（LE） |
| `int16()` | `int` | 符号付き 16 ビット整数（LE） |
| `uint32()` | `int` | 符号なし 32 ビット整数（LE） |
| `int32()` | `int` | 符号付き 32 ビット整数（LE） |
| `be_int32()` | `int` | 符号付き 32 ビット整数（BE） |
| `uint64()` | `int` | 符号なし 64 ビット整数（LE） |
| `int64()` | `int` | 符号付き 64 ビット整数（LE） |
| `float32()` | `float` | 32 ビット浮動小数点数（LE） |
| `float64()` | `float` | 64 ビット浮動小数点数（LE） |

### 可変長整数（Varint / LEB128 / Zigzag）

| メソッド | 戻り値 | 説明 |
|---|---|---|
| `varuint32()` | `int` | 符号なし 32 ビット varint |
| `varint32()` | `int` | 符号付き 32 ビット varint（zigzag） |
| `varuint64()` | `int` | 符号なし 64 ビット varint |
| `varint64()` | `int` | 符号付き 64 ビット varint（zigzag） |

### 文字列・バイト列

| メソッド | 戻り値 | 説明 |
|---|---|---|
| `string()` | `str` | varuint32 長プレフィックス付き UTF-8 文字列 |
| `string_utf()` | `str` | int16 長プレフィックス付き UTF-8 文字列 |
| `byte_slice()` | `bytes` | varuint32 長プレフィックス付きバイト列 |
| `bytes_remaining()` | `bytes` | 残りすべてのバイトを読み取る |

### Minecraft 固有型

| メソッド | 戻り値 | 説明 |
|---|---|---|
| `vec3()` | `Vec3` | 3D ベクトル（float32 x 3） |
| `vec2()` | `Vec2` | 2D ベクトル（float32 x 2） |
| `block_pos()` | `BlockPos` | ブロック位置（varint32 x 3） |
| `chunk_pos()` | `ChunkPos` | チャンク位置（varint32 x 2） |
| `sub_chunk_pos()` | `SubChunkPos` | サブチャンク位置（varint32 x 3） |
| `sound_pos()` | `Vec3` | サウンド位置（block_pos / 8.0） |
| `byte_float()` | `float` | バイト角度（uint8 * 360/256） |
| `uuid()` | `UUID` | UUID（16 バイト、LE ハーフリバース） |
| `rgb()` | `RGBA` | RGB カラー（float32 x 3、A=255） |
| `rgba()` | `RGBA` | RGBA カラー（uint32） |
| `argb()` | `RGBA` | ARGB カラー（int32、LE） |
| `be_argb()` | `RGBA` | ARGB カラー（int32、BE） |
| `var_rgba()` | `RGBA` | RGBA カラー（varuint32） |
| `nbt()` | `dict` | NBT データ（NetworkLittleEndian） |

### コレクション・ヘルパー

| メソッド | 説明 |
|---|---|
| `read_slice(read_fn)` | varuint32 長の配列を読み取る |
| `read_slice_uint8(read_fn)` | uint8 長の配列を読み取る |
| `read_slice_uint16(read_fn)` | uint16 長の配列を読み取る |
| `read_slice_uint32(read_fn)` | uint32 長の配列を読み取る |
| `read_optional(read_fn)` | bool プレフィックス付きオプショナル値 |

---

## PacketWriter

`mcbe.proto.io.PacketWriter` — バイナリデータをプロトコル形式で書き込むライター。

### コンストラクタ

```python
PacketWriter(buf: BytesIO | None = None)
```

### メソッド

`data() -> bytes` でバッファの内容を取得する。

`PacketReader` と対称的な write メソッドを持つ:

- **プリミティブ**: `uint8(v)`, `int8(v)`, `bool(v)`, `uint16(v)`, `int16(v)`, `uint32(v)`, `int32(v)`, `be_int32(v)`, `uint64(v)`, `int64(v)`, `float32(v)`, `float64(v)`
- **Varint**: `varuint32(v)`, `varint32(v)`, `varuint64(v)`, `varint64(v)`
- **文字列**: `string(v)`, `string_utf(v)`, `byte_slice(v)`, `bytes_raw(v)`
- **Minecraft 型**: `vec3(v)`, `vec2(v)`, `block_pos(v)`, `chunk_pos(v)`, `sub_chunk_pos(v)`, `sound_pos(v)`, `byte_float(v)`, `uuid(v)`, `rgb(v)`, `rgba(v)`, `argb(v)`, `be_argb(v)`, `var_rgba(v)`, `nbt(v)`
- **コレクション**: `write_slice(items, write_fn)`, `write_slice_uint8(items, write_fn)`, `write_slice_uint16(items, write_fn)`, `write_slice_uint32(items, write_fn)`, `write_optional(value, write_fn)`

---

## Packet 基底クラス

```python
class Packet(ABC):
    packet_id: int = 0

    @abstractmethod
    def write(self, w: PacketWriter) -> None: ...

    @classmethod
    @abstractmethod
    def read(cls, r: PacketReader) -> Packet: ...
```

すべてのパケットが実装すべき抽象基底クラス。

### UnknownPacket

```python
@dataclass
class UnknownPacket(Packet):
    packet_id: int = 0
    payload: bytes = b""
```

登録されていないパケット ID を持つパケットを表す。ペイロードはそのまま保持される。

---

## パケット登録デコレータ

| デコレータ | 説明 |
|---|---|
| `@register_server_packet` | サーバー発信パケットとして登録（クライアントの受信プール） |
| `@register_client_packet` | クライアント発信パケットとして登録（サーバーの受信プール） |
| `@register_bidirectional` | 双方向パケットとして登録（両方のプールに登録） |

### パケットプール取得

```python
def server_pool() -> PacketPool  # サーバー発信パケットのプール（コピー）
def client_pool() -> PacketPool  # クライアント発信パケットのプール（コピー）
```

`PacketPool` は `dict[int, Type[Packet]]` の型エイリアス。

---

## エンコード・デコード関数

### パケット単体

```python
def encode_packet(pk: Packet) -> bytes
def decode_packet(data: bytes, pool: PacketPool) -> Packet
```

`encode_packet` はパケットヘッダー（varuint32 のパケット ID）とペイロードをバイト列にエンコードする。

`decode_packet` はバイト列をヘッダーから解析し、プール内のクラスでデコードする。見つからない場合は `UnknownPacket` として返す。

### バッチ

```python
def encode_batch(
    packets: list[bytes],
    compression: int | None = None,
    compression_threshold: int = 256,
    use_batch_header: bool = True,
) -> bytes

def decode_batch(
    data: bytes,
    compression: int | None = None,
    max_decompressed: int = 16 * 1024 * 1024,
    use_batch_header: bool = True,
) -> list[bytes]
```

バッチは複数のエンコード済みパケットを単一ペイロードにまとめる。各パケットは varuint32 長プレフィックス付き。

---

## 圧縮定数

| 定数 | 値 | 説明 |
|---|---|---|
| `COMPRESSION_NONE` | `0xFF` | 圧縮なし（閾値以下のデータ用マーカー） |
| `COMPRESSION_FLATE` | `0x00` | Raw Deflate（zlib ヘッダーなし） |
| `COMPRESSION_SNAPPY` | `0x01` | Snappy 圧縮 |
| `BATCH_HEADER` | `0xFE` | バッチヘッダーバイト |
| `MAX_BATCH_SIZE` | `812` | 単一バッチの最大パケット数 |

---

## 暗号化

`mcbe.proto.encryption` モジュール。AES-256-CTR + SHA-256 チェックサムによるパケット暗号化。

### PacketEncrypt

```python
class PacketEncrypt:
    def __init__(self, key_bytes: bytes) -> None  # 32 バイト鍵
    def encrypt(self, data: bytearray) -> bytearray
```

バッチデータを暗号化する。バイト 0（ヘッダー）は暗号化されず、バイト 1 以降が暗号化される。暗号化前に 8 バイトの SHA-256 チェックサムが付加される。

IV: 鍵の先頭 12 バイト + `\x00\x00\x00\x02`

### PacketDecrypt

```python
class PacketDecrypt:
    def __init__(self, key_bytes: bytes) -> None  # 32 バイト鍵
    def decrypt_and_verify(self, data: bytes) -> bytes
```

データを復号し、チェックサムを検証する。不正なチェックサムの場合は `ValueError` を送出する。

### ヘルパー関数

```python
def derive_key(salt: bytes, shared_secret: bytes) -> bytes
```
32 バイトの暗号化鍵を導出する: `SHA256(salt || shared_secret)`

```python
def compute_shared_secret(private_key, peer_public_key) -> bytes
```
P-384 鍵ペアを使った ECDH 共有シークレットを計算する（48 バイト）。

---

## プロトコル型

`mcbe.proto.types` モジュールで定義される基本型。

### 位置型（NamedTuple）

| 型 | フィールド | 説明 |
|---|---|---|
| `BlockPos` | `x: int, y: int, z: int` | ブロック位置 |
| `ChunkPos` | `x: int, z: int` | チャンク位置 |
| `SubChunkPos` | `x: int, y: int, z: int` | サブチャンク位置 |
| `Vec2` | `x: float, y: float` | 2D ベクトル（float32） |
| `Vec3` | `x: float, y: float, z: float` | 3D ベクトル（float32） |

### カラー

```python
@dataclass
class RGBA:
    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 255
```

| メソッド | 説明 |
|---|---|
| `to_uint32() -> int` | RGBA バイトオーダーで uint32 にエンコード |
| `RGBA.from_uint32(v) -> RGBA` | uint32 からデコード |

### ゲームデータ型

| 型 | 主なフィールド | 説明 |
|---|---|---|
| `GameRule` | `name`, `can_be_modified_by_player`, `value` | ゲームルール |
| `Attribute` | `name`, `value`, `max`, `min`, `default` | エンティティ属性 |
| `AttributeModifier` | `id`, `name`, `amount`, `operation` | 属性修飾子 |
| `AttributeValue` | `name`, `min`, `max`, `value`, `default`, `modifiers` | 修飾子付き属性 |
| `AbilityLayer` | `layer_type`, `abilities`, `values`, `fly_speed`, `walk_speed` | アビリティレイヤー |
| `AbilityData` | `entity_unique_id`, `player_permissions`, `command_permissions`, `layers` | プレイヤーアビリティ |
| `ItemStack` | `network_id`, `count`, `metadata`, `block_runtime_id` | アイテムスタック |
| `ItemInstance` | `stack_network_id`, `stack` | アイテムインスタンス |
| `ExperimentData` | `name`, `enabled` | 実験的機能 |
| `BlockEntry` | `name`, `properties` | カスタムブロックエントリ |
