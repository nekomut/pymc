# 認証モジュール

`mcbe.auth` パッケージは、Minecraft Bedrock Edition のオンライン認証に必要なすべてのステップを提供する。

認証フロー全体:

```
Microsoft Live (OAuth2)
  → Xbox Live (XSTS)
    → PlayFab (セッションチケット)
      → Minecraft Services (MCToken / マルチプレイヤートークン)
        → Minecraft Auth (JWT チェーン)
```

---

## auth.live — Microsoft Live Connect

Microsoft Live Connect の OAuth2 デバイスコードフローを実装する。

### Token クラス

```python
@dataclass
class Token:
    access_token: str
    token_type: str
    refresh_token: str
    expiry: float  # Unix タイムスタンプ
```

| メソッド | 説明 |
|---|---|
| `valid() -> bool` | トークンが有効期限内かどうか（1分のバッファ付き） |
| `to_dict() -> dict` | 辞書に変換 |
| `Token.from_dict(data) -> Token` | 辞書から復元 |

### Config クラス

```python
@dataclass
class Config:
    client_id: str
    device_type: str
    version: str
    user_agent: str
```

デバイス構成。以下の定義済み設定が利用可能:

| 定数 | デバイス | client_id |
|---|---|---|
| `ANDROID_CONFIG` | Android | `0000000048183522` |
| `IOS_CONFIG` | iOS | `000000004c17c01a` |
| `WIN32_CONFIG` | Win32 | `0000000040159362` |
| `NINTENDO_CONFIG` | Nintendo | `00000000441cc96b` |
| `PLAYSTATION_CONFIG` | PlayStation | `000000004827c78e` |

### `get_live_token()`

```python
async def get_live_token(
    config: Config | None = None,
    writer: IO[str] | None = None,
    session: aiohttp.ClientSession | None = None,
    cache_path: Path | str | None = None,
) -> Token
```

キャッシュ付きでトークンを取得する。

1. `~/.mcbe/token_cache.json` からキャッシュを読み込み、有効ならそのまま返す
2. 期限切れなら `refresh_token` で更新
3. キャッシュがない / refresh 失敗ならデバイスコードフローでブラウザ認証

### `request_live_token()`

```python
async def request_live_token(
    config: Config | None = None,
    writer: IO[str] | None = None,
    session: aiohttp.ClientSession | None = None,
) -> Token
```

デバイスコードフローで認証 URL とコードを表示し、ユーザーが認証を完了するまでポーリングする。

### `refresh_token()`

```python
async def refresh_token(
    token: Token,
    config: Config | None = None,
    session: aiohttp.ClientSession | None = None,
) -> Token
```

期限切れの OAuth2 トークンをリフレッシュする。

### ヘルパー関数

| 関数 | 説明 |
|---|---|
| `save_token(token, path=None)` | トークンをファイルに保存 |
| `load_token(path=None) -> Token \| None` | 保存済みトークンを読み込み |
| `server_time() -> float` | 推定サーバー時刻を返す |

---

## auth.xbox — Xbox Live 認証

ECDSA P-256 署名付きリクエストによるデバイストークン取得と XSTS トークン交換を行う。

### XBLToken クラス

```python
@dataclass
class XBLToken:
    token: str = ""
    user_hash: str = ""
    gamer_tag: str = ""
    xuid: str = ""
    issue_instant: str = ""
    not_after: str = ""
```

| メソッド | 説明 |
|---|---|
| `valid() -> bool` | トークンが有効期限内か |
| `auth_header_value() -> str` | `"XBL3.0 x={user_hash};{token}"` 形式のヘッダー値 |
| `set_auth_header(headers)` | 辞書に `Authorization` ヘッダーを設定 |

### `request_xbl_token()`

```python
async def request_xbl_token(
    live_token: Token,
    relying_party: str,
    config: Config | None = None,
    session: aiohttp.ClientSession | None = None,
) -> XBLToken
```

Xbox Live XSTS トークンを取得する。

| パラメータ | 説明 |
|---|---|
| `live_token` | 有効な Microsoft Live OAuth2 トークン |
| `relying_party` | リライングパーティ URL（例: `"https://multiplayer.minecraft.net/"`） |
| `config` | デバイス設定。デフォルトは `ANDROID_CONFIG` |

デバイストークンのレートリミットに対応するため、プライマリ設定が失敗した場合は自動的に他のデバイスタイプにフォールバックする。

---

## auth.minecraft — Minecraft 認証

Xbox Live トークンと ECDSA 秘密鍵を使って Minecraft JWT チェーンをリクエストする。

### `request_minecraft_chain()`

```python
async def request_minecraft_chain(
    xbl_token: XBLToken,
    private_key: EllipticCurvePrivateKey,
    session: aiohttp.ClientSession | None = None,
) -> str
```

| パラメータ | 説明 |
|---|---|
| `xbl_token` | 有効な Xbox Live XSTS トークン |
| `private_key` | クライアントの ECDSA P-384 秘密鍵（暗号化にも使用される） |

**戻り値**: Login パケットで使用する生の JWT チェーン文字列。

---

## auth.playfab — PlayFab 認証

Xbox Live トークンを使って PlayFab にログインし、セッションチケットを取得する。

### `login_with_xbox()`

```python
async def login_with_xbox(
    xbl_token: XBLToken,
    title_id: str = "20CA2",
    session: aiohttp.ClientSession | None = None,
) -> str
```

| パラメータ | 説明 |
|---|---|
| `xbl_token` | リライングパーティ `http://playfab.xboxlive.com/` で取得した XBL トークン |
| `title_id` | PlayFab タイトル ID（デフォルト: `"20CA2"`） |

**戻り値**: PlayFab セッションチケット文字列。

---

## auth.service — Minecraft Services

Discovery API を介してサービスエンドポイントを解決し、MCToken（サービストークン）とマルチプレイヤートークンを取得する。

### データクラス

#### `SignalingInfo`

```python
@dataclass
class SignalingInfo:
    service_uri: str = ""   # WebSocket シグナリング URL
    stun_uri: str = ""      # STUN サーバー URL
    turn_uri: str = ""      # TURN サーバー URL
```

#### `ServiceToken`

```python
@dataclass
class ServiceToken:
    authorization_header: str = ""  # MCToken JWT
    valid_until: str = ""           # ISO 8601 有効期限
    treatments: list[str] = field(default_factory=list)
    treatment_context: str = ""
```

| メソッド | 説明 |
|---|---|
| `valid() -> bool` | トークンが有効期限内か |

#### `DiscoveryResult`

```python
@dataclass
class DiscoveryResult:
    raw: dict = field(default_factory=dict)
    env: str = "prod"
```

| プロパティ | 説明 |
|---|---|
| `auth_uri -> str` | 認可サービスの URI |
| `playfab_title_id -> str` | PlayFab タイトル ID |
| `signaling_info -> SignalingInfo` | シグナリングサービス情報 |

### `discover()`

```python
async def discover(
    version: str = GAME_VERSION,
    session: aiohttp.ClientSession | None = None,
) -> DiscoveryResult
```

Discovery API からサービスエンドポイントを取得する。環境（prod/stage/dev）は `supportedEnvironments` から自動判定される。

### `request_service_token()`

```python
async def request_service_token(
    service_uri: str,
    xbox_token: str,
    playfab_title_id: str = "20CA2",
    version: str = GAME_VERSION,
    session: aiohttp.ClientSession | None = None,
    *,
    playfab_session_ticket: str = "",
) -> ServiceToken
```

認可サービスからサービストークン（MCToken）を取得する。`playfab_session_ticket` が指定されている場合は PlayFab 認証を使用し、それ以外は Xbox トークンを使用する。

### `request_multiplayer_token()`

```python
async def request_multiplayer_token(
    service_uri: str,
    service_token: ServiceToken,
    public_key: ec.EllipticCurvePublicKey,
    session: aiohttp.ClientSession | None = None,
) -> str
```

マルチプレイヤートークン（OIDC JWT）を取得する。トークンはクライアントの公開鍵にバインドされ（`cpk` クレーム）、Login パケットの接続リクエストで使用される。

### ヘルパー関数

| 関数 | 説明 |
|---|---|
| `discover_auth_uri(version) -> str` | 認可サービス URI を取得 |
| `discover_signaling(version) -> SignalingInfo` | シグナリング情報を取得 |
