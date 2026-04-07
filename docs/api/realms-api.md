# RealmsClient

`mcbe.realms` モジュールは、Minecraft Bedrock Edition の Realms API への非同期アクセスを提供する。

---

## RealmsClient クラス

```python
from mcbe.realms import RealmsClient
```

Realms API の非同期クライアント。

### コンストラクタ

```python
RealmsClient(
    xbl_token: XBLToken,
    session: aiohttp.ClientSession | None = None,
)
```

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `xbl_token` | `XBLToken` | (必須) | リライングパーティ `https://pocket.realms.minecraft.net/` で取得した Xbox Live トークン |
| `session` | `aiohttp.ClientSession \| None` | `None` | 再利用する HTTP セッション。`None` の場合は自動生成 |

### コンテキストマネージャ

```python
async with RealmsClient(xbl_token) as client:
    realms = await client.realms()
```

`__aenter__` で HTTP セッションを初期化し、`__aexit__` で自動クローズする。

### メソッド

#### `realms() -> list[Realm]`

```python
async def realms() -> list[Realm]
```

認証済みユーザーがアクセス可能なすべての Realm を取得する。

#### `realm(code: str) -> Realm`

```python
async def realm(code: str) -> Realm
```

招待コードから Realm を取得する。

---

## Realm データクラス

```python
from mcbe.realms import Realm
```

Realms API から返される Realm 情報。

### プロパティ

| プロパティ | 型 | 説明 |
|---|---|---|
| `id` | `int` | Realm ID |
| `remote_subscription_id` | `str` | リモートサブスクリプション ID |
| `owner` | `str` | オーナーのゲーマータグ |
| `owner_uuid` | `str` | オーナーの UUID |
| `name` | `str` | Realm 名 |
| `motd` | `str` | MOTD（メッセージ） |
| `default_permission` | `str` | デフォルト権限 |
| `state` | `str` | 状態（例: `"OPEN"`, `"CLOSED"`） |
| `days_left` | `int` | 残りの有効日数 |
| `expired` | `bool` | 有効期限切れか |
| `expired_trial` | `bool` | 試用期間切れか |
| `grace_period` | `bool` | 猶予期間中か |
| `world_type` | `str` | ワールドタイプ |
| `players` | `list[Player]` | プレイヤーリスト |
| `max_players` | `int` | 最大プレイヤー数 |
| `active_slot` | `int` | アクティブなワールドスロット |
| `member` | `bool` | メンバーかどうか |
| `club_id` | `int` | クラブ ID |

### メソッド

#### `address() -> RealmAddress`

```python
async def address() -> RealmAddress
```

この Realm の接続アドレスを取得する。Realm が起動中（HTTP 503）の場合は自動的にリトライする。

#### `online_players() -> list[Player]`

```python
async def online_players() -> list[Player]
```

現在オンラインのプレイヤーを取得する。Realm オーナーのみ呼び出し可能（他のユーザーは 403 エラー）。

---

## RealmAddress データクラス

```python
@dataclass
class RealmAddress:
    address: str = ""              # 接続アドレス（host:port 形式）
    network_protocol: str = ""     # "raknet" または "nethernet"
```

---

## Player データクラス

```python
@dataclass
class Player:
    uuid: str = ""
    name: str = ""
    operator: bool = False
    accepted: bool = False
    online: bool = False
    permission: str = ""
```

---

## コード例

```python
import asyncio
from mcbe.auth.live import get_live_token
from mcbe.auth.xbox import request_xbl_token
from mcbe.realms import RealmsClient

async def main():
    live_token = await get_live_token()
    xbl_token = await request_xbl_token(
        live_token, "https://pocket.realms.minecraft.net/"
    )

    async with RealmsClient(xbl_token) as client:
        realms = await client.realms()
        for realm in realms:
            print(f"{realm.name} (owner: {realm.owner})")

        if realms:
            addr = await realms[0].address()
            print(f"接続先: {addr.address} ({addr.network_protocol})")

asyncio.run(main())
```
