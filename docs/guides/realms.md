# Realms 接続ガイド

Realms への接続は BDS/LAN と比べて複雑です。Microsoft アカウント認証、Xbox Live トークン取得、PlayFab ログイン、シグナリングを経て WebRTC DataChannel で接続します。

## 接続手順

### Step 1: Microsoft Live OAuth2

デバイスコードフローで Microsoft アカウントのアクセストークンを取得します。初回実行時にブラウザでのログインが必要です。

```python
from mcbe.auth.live import get_live_token

live_token = await get_live_token()
```

### Step 2: Xbox Live トークン (Realms API 用)

Realms API のリライングパーティを指定して Xbox Live トークンを取得します。

```python
from mcbe.auth.xbox import request_xbl_token

xbl_realms = await request_xbl_token(live_token, "https://pocket.realms.minecraft.net/")
```

### Step 3: Realms API で Realm アドレスを取得

```python
from mcbe.realms import RealmsClient

async with RealmsClient(xbl_realms) as client:
    # 招待コードで特定の Realm を取得
    realm = await client.realm(invite_code)
    # または、アクセス可能な全 Realm を一覧
    realms = await client.realms()
    realm = realms[0]

    realm_addr = await realm.address()
```

### Step 4: プロトコル判定

Realm のネットワークプロトコルを確認します。`NETHERNET` の場合は WebRTC を使います。

```python
address = realm_addr.address
is_nethernet = realm_addr.network_protocol and "NETHERNET" in realm_addr.network_protocol.upper()
is_jsonrpc = is_nethernet and "JSONRPC" in realm_addr.network_protocol.upper()
```

### Step 5: PlayFab ログインと Discovery

PlayFab 用の Xbox Live トークンを取得し、Discovery API で認証・シグナリングの各 URI を取得します。

```python
from mcbe.auth.service import discover, request_service_token, request_multiplayer_token
from mcbe.auth.playfab import login_with_xbox as playfab_login

xbl_pf = await request_xbl_token(live_token, "http://playfab.xboxlive.com/")
discovery = await discover()
playfab_ticket = await playfab_login(xbl_pf, title_id=discovery.playfab_title_id)
```

### Step 6: MCToken (Service Token) と Multiplayer Token

```python
from cryptography.hazmat.primitives.asymmetric import ec

key = ec.generate_private_key(ec.SECP384R1())

service_token = await request_service_token(
    discovery.auth_uri, xbl_pf.auth_header_value(),
    playfab_title_id=discovery.playfab_title_id,
    playfab_session_ticket=playfab_ticket,
)
multiplayer_token = await request_multiplayer_token(
    discovery.auth_uri, service_token, key.public_key(),
)
```

### Step 7: NetherNet ネットワーク作成

```python
from mcbe.nethernet import create_network

network = create_network(
    mc_token=service_token.authorization_header,
    signaling_url=discovery.signaling_info.service_uri,
    use_jsonrpc=is_jsonrpc,
)
```

### Step 8: Minecraft Chain JWT

マルチプレイヤー用の Xbox Live トークンを取得し、Minecraft 認証チェーン JWT を作成します。

```python
from mcbe.auth.minecraft import request_minecraft_chain

xbl_mp = await request_xbl_token(live_token, "https://multiplayer.minecraft.net/")
login_chain = await request_minecraft_chain(xbl_mp, key)
```

### Step 9: Dialer で接続

全てのトークンを Dialer に渡して接続します。

```python
from mcbe.dial import Dialer
from mcbe.proto.login.data import IdentityData

dialer = Dialer(
    identity_data=IdentityData(display_name="mcbe"),
    network=network,
    login_chain=login_chain,
    auth_key=key,
    multiplayer_token=multiplayer_token,
)

async with await dialer.dial(address) as conn:
    print("Realms に接続完了!")
    # パケットの読み書き...
```

## 完全なコード

`examples/place_block.py` の `resolve_realms()` 関数に、上記の全手順をまとめた実装があります。

```python
async def resolve_realms(invite_code=None):
    """Realms に認証して接続情報を返す."""
    from mcbe.auth.live import get_live_token
    from mcbe.auth.xbox import request_xbl_token
    from mcbe.auth.minecraft import request_minecraft_chain

    live_token = await get_live_token()

    # Realms API
    from mcbe.realms import RealmsClient
    xbl_realms = await request_xbl_token(live_token, "https://pocket.realms.minecraft.net/")
    async with RealmsClient(xbl_realms) as client:
        if invite_code:
            realm = await client.realm(invite_code)
        else:
            realms = await client.realms()
            if not realms:
                raise RuntimeError("アクセス可能な Realm がありません")
            realm = realms[0]
        realm_addr = await realm.address()

    address = realm_addr.address
    is_nethernet = realm_addr.network_protocol and "NETHERNET" in realm_addr.network_protocol.upper()
    is_jsonrpc = is_nethernet and "JSONRPC" in realm_addr.network_protocol.upper()

    key = ec.generate_private_key(ec.SECP384R1())
    network = None
    multiplayer_token = ""

    if is_nethernet:
        from mcbe.auth.service import discover, request_service_token, request_multiplayer_token
        from mcbe.auth.playfab import login_with_xbox as playfab_login
        from mcbe.nethernet import create_network

        xbl_pf = await request_xbl_token(live_token, "http://playfab.xboxlive.com/")
        discovery = await discover()
        playfab_ticket = await playfab_login(xbl_pf, title_id=discovery.playfab_title_id)
        service_token = await request_service_token(
            discovery.auth_uri, xbl_pf.auth_header_value(),
            playfab_title_id=discovery.playfab_title_id,
            playfab_session_ticket=playfab_ticket,
        )
        multiplayer_token = await request_multiplayer_token(
            discovery.auth_uri, service_token, key.public_key(),
        )
        network = create_network(
            mc_token=service_token.authorization_header,
            signaling_url=discovery.signaling_info.service_uri,
            use_jsonrpc=is_jsonrpc,
        )

    xbl_mp = await request_xbl_token(live_token, "https://multiplayer.minecraft.net/")
    login_chain = await request_minecraft_chain(xbl_mp, key)

    return address, login_chain, key, multiplayer_token, network
```

## 参考

- `examples/place_block.py` --- `resolve_realms()` 関数
- `examples/conn_realms.py` --- Realms 接続サンプル
