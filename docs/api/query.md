# UT3 クエリ

`mcbe.query` モジュールは、Minecraft Bedrock Edition サーバーに対して UT3 (Unreal Tournament 3) クエリプロトコルを使用してサーバー情報を取得する機能を提供する。

---

## query() 関数

```python
from mcbe.query import query

async def query(
    address: str,
    timeout: float = 5.0,
) -> dict[str, str]
```

Minecraft Bedrock サーバーにクエリを送信し、サーバー情報を取得する。

### パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `address` | `str` | (必須) | サーバーアドレス（`"host:port"` 形式） |
| `timeout` | `float` | `5.0` | タイムアウト（秒） |

### 戻り値

サーバー情報のキーと値の辞書 (`dict[str, str]`)。

一般的なキー:

| キー | 説明 |
|---|---|
| `hostname` | サーバー名 |
| `gametype` | ゲームタイプ（例: `"SMP"`） |
| `map` | マップ名 |
| `numplayers` | 現在のプレイヤー数 |
| `maxplayers` | 最大プレイヤー数 |
| `hostport` | ポート番号 |
| `hostip` | ホスト IP |
| `version` | ゲームバージョン |

### プロトコル概要

1. **ハンドシェイク**: UDP でクエリタイプ 9 のリクエストを送信し、レスポンス番号を取得
2. **情報リクエスト**: レスポンス番号を含むクエリタイプ 0 のリクエストを送信し、サーバー情報を取得

---

## コード例

```python
import asyncio
from mcbe.query.query import query

async def main():
    info = await query("play.example.com:19132")
    print(f"サーバー名: {info.get('hostname', 'N/A')}")
    print(f"プレイヤー: {info.get('numplayers', '?')}/{info.get('maxplayers', '?')}")
    print(f"マップ: {info.get('map', 'N/A')}")
    print(f"バージョン: {info.get('version', 'N/A')}")

asyncio.run(main())
```
