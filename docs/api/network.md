# Network 抽象レイヤー

`mcbe.network` モジュールは、Minecraft Bedrock Edition のトランスポート層を抽象化するインターフェースを定義する。RakNet、NetherNet（WebRTC）、TCP（テスト用）などの実装を差し替えて使用できる。

---

## Network ABC

```python
class Network(ABC):
```

トランスポート層の抽象基底クラス。

### メソッド

#### `connect(address: str) -> NetworkConnection`

```python
async def connect(address: str) -> NetworkConnection
```

`"host:port"` 形式のアドレスにあるサーバーへ接続する。

#### `ping(address: str) -> bytes`

```python
async def ping(address: str) -> bytes
```

サーバーに ping を送り、pong データを返す。

#### `listen(address: str) -> NetworkListener`

```python
async def listen(address: str) -> NetworkListener
```

指定アドレスで接続を待ち受ける `NetworkListener` を開始する。

---

## NetworkConnection ABC

```python
class NetworkConnection(ABC):
```

トランスポートレベルの接続を表す抽象基底クラス。

### メソッド

| メソッド | シグネチャ | 説明 |
|---|---|---|
| `read_packet()` | `async def read_packet() -> bytes` | 生パケットを1つ読み取る。データが利用可能になるまでブロックする |
| `write_packet(data)` | `async def write_packet(data: bytes) -> None` | 生パケットを1つ書き込む |
| `close()` | `async def close() -> None` | 接続を閉じる |

---

## NetworkListener ABC

```python
class NetworkListener(ABC):
```

接続を受け入れるリスナーの抽象基底クラス。

### メソッド

| メソッド | シグネチャ | 説明 |
|---|---|---|
| `accept()` | `async def accept() -> NetworkConnection` | 新しい接続を受け入れる |
| `set_pong_data(data)` | `def set_pong_data(data: bytes) -> None` | サーバーステータス（pong）のレスポンスデータを設定する |
| `server_id()` | `def server_id() -> int` | セッション固有のサーバー ID を返す |
| `close()` | `async def close() -> None` | リスナーを停止して閉じる |

---

## RakNetNetwork クラス

```python
from mcbe.raknet.network import RakNetNetwork
```

RakNet プロトコルを使用した `Network` 実装。実際の Minecraft Bedrock Edition サーバーへの接続に使用する。

### コンストラクタ

```python
RakNetNetwork(client_guid: int | None = None)
```

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `client_guid` | `int \| None` | `None` | クライアント GUID。`None` の場合はランダム生成 |

### メソッド

- `connect(address)` — UDP 経由で RakNet ハンドシェイク（MTU ネゴシエーション → ConnectionRequest）を行い接続する
- `ping(address)` — UnconnectedPing を送信し、pong データを返す
- `listen(address)` — RakNet リスナーを開始する

### MTU ネゴシエーション

接続時、MTU サイズを大きい順に試行する:
- MAX_MTU → DEFAULT_MTU → MIN_MTU

---

## NetherNet (WebRTC)

```python
from mcbe.nethernet import create_network
```

WebRTC ベースのネットワーク実装。Realms で使用される NETHERNET_JSONRPC プロトコルに対応する。

### `create_network()` ファクトリ関数

```python
def create_network(
    *,
    mc_token: str,
    signaling_url: str = "",
    use_jsonrpc: bool = False,
    backend: str | None = None,
)
```

最適なバックエンドを自動選択して NetherNet Network インスタンスを返す。

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `mc_token` | `str` | (必須) | MCToken 認可ヘッダー値 |
| `signaling_url` | `str` | `""` | WebSocket シグナリングサーバー URL |
| `use_jsonrpc` | `bool` | `False` | JSON-RPC シグナリングを使用するか |
| `backend` | `str \| None` | `None` | バックエンドを強制指定。`None` の場合は自動検出 |

### バックエンド

| バックエンド | 説明 |
|---|---|
| `"libdatachannel"` | C++ ネイティブ実装（usrsctp / OpenSSL ベース）。インストール済みなら優先される |
| `"aiortc"` | Pure Python 実装。基本依存として含まれ、BDS 互換パッチ済み |

自動検出 (`backend=None`) の場合、`libdatachannel` が利用可能であればそちらが優先される。

---

## TCPNetwork（テスト用）

```python
from mcbe.network import TCPNetwork
```

TCP ベースのトランスポート。長さプレフィックス付きパケット（4 バイト ビッグエンディアン）を使用する。RakNet 依存なしのテスト用。

---

## ヘルパー関数

### `format_pong_data()`

```python
def format_pong_data(
    server_name: str,
    protocol_version: int,
    game_version: str,
    player_count: int,
    max_players: int,
    server_id: int,
    sub_name: str = "mcbe",
    game_mode: str = "Survival",
    port: int = 19132,
) -> bytes
```

Minecraft Bedrock Edition のサーバーステータス pong データをフォーマットする。
