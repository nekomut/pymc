# NBT (Named Binary Tag)

`mcbe.nbt` モジュールは、Minecraft の NBT (Named Binary Tag) シリアライゼーションを提供する。

---

## 概要

NBT は Minecraft で使用されるバイナリフォーマットで、ワールドデータやネットワークプロトコルでの構造化データの保存に使われる。このモジュールは3つのエンコーディングバリアントをサポートする。

---

## encode()

```python
def encode(
    value: Any,
    encoding: Encoding | None = None,
    name: str = "",
) -> bytes
```

Python の値を NBT バイト列にエンコードする。

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `value` | `Any` | (必須) | エンコードする値。通常は `dict`（compound tag） |
| `encoding` | `Encoding \| None` | `None` | NBT エンコーディング。`None` の場合は `NetworkLittleEndian` |
| `name` | `str` | `""` | ルートタグ名（ネットワーク NBT では通常空文字列） |

---

## decode()

```python
def decode(
    data: bytes,
    encoding: Encoding | None = None,
    allow_zero: bool = True,
) -> dict[str, Any]
```

NBT バイト列を Python の辞書にデコードする。

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `data` | `bytes` | (必須) | 生の NBT バイト列 |
| `encoding` | `Encoding \| None` | `None` | NBT エンコーディング。`None` の場合は `NetworkLittleEndian` |
| `allow_zero` | `bool` | `True` | 先頭が TAG_End の場合に空辞書を返すか |

---

## エンコーディングバリアント

```python
from mcbe.nbt import NetworkLittleEndian, LittleEndian, BigEndian
```

| バリアント | 整数型 | 文字列長 | 用途 |
|---|---|---|---|
| `NetworkLittleEndian` | varint（zigzag） | varuint32 | ネットワークプロトコル（デフォルト） |
| `LittleEndian` | 固定長 LE | uint16 LE | Bedrock Edition ワールドセーブ |
| `BigEndian` | 固定長 BE | uint16 BE | Java Edition |

---

## Python 型マッピング

NBT タグ型は Python の型から自動推論される:

| Python 型 | NBT タグ | 条件 |
|---|---|---|
| `bool` | TAG_Byte | - |
| `int` (0-127) | TAG_Byte | - |
| `int` (-32768-32767) | TAG_Short | - |
| `int` (-2^31-2^31-1) | TAG_Int | - |
| `int` (それ以外) | TAG_Long | - |
| `float` | TAG_Float | - |
| `str` | TAG_String | - |
| `bytes` / `bytearray` | TAG_Byte_Array | - |
| `dict` | TAG_Compound | - |
| `list` | TAG_List | 要素型は最初の要素から推論 |

---

## コード例

### ネットワーク NBT（デフォルト）

```python
from mcbe.nbt import encode, decode

# エンコード
data = encode({
    "Level": {
        "SpawnX": 100,
        "SpawnY": 64,
        "SpawnZ": 200,
        "LevelName": "My World",
    }
})

# デコード
result = decode(data)
print(result["Level"]["LevelName"])  # "My World"
```

### Bedrock ワールドセーブ（LittleEndian）

```python
from mcbe.nbt import encode, decode, LittleEndian

data = encode({"key": "value"}, encoding=LittleEndian)
result = decode(data, encoding=LittleEndian)
```

### Java Edition（BigEndian）

```python
from mcbe.nbt import encode, decode, BigEndian

data = encode({"key": "value"}, encoding=BigEndian)
result = decode(data, encoding=BigEndian)
```
