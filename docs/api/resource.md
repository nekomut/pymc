# リソースパック

`mcbe.resource` パッケージは、Minecraft Bedrock Edition のリソースパック / ビヘイビアパックの読み込みと管理を提供する。

---

## Pack クラス

```python
from mcbe.resource.pack import Pack
```

リソースパック / ビヘイビアパックを表すクラス。

### フィールド

| フィールド | 型 | 説明 |
|---|---|---|
| `manifest` | `Manifest` | パックのマニフェスト |
| `content` | `bytes` | パックの ZIP コンテンツ |
| `content_key` | `str` | 暗号化キー（暗号化パックの場合） |
| `download_url` | `str` | ダウンロード URL |

### プロパティ

| プロパティ | 型 | 説明 |
|---|---|---|
| `name` | `str` | パック名（マニフェストのヘッダーから取得） |
| `uuid` | `str` | パック UUID |
| `description` | `str` | パックの説明 |
| `version` | `str` | バージョン文字列（例: `"1.0.0"`） |

### メソッド

| メソッド | 戻り値 | 説明 |
|---|---|---|
| `has_scripts()` | `bool` | クライアントデータ（スクリプト）モジュールを含むか |
| `has_textures()` | `bool` | リソース（テクスチャ）モジュールを含むか |
| `has_behaviours()` | `bool` | データ（ビヘイビア）モジュールを含むか |
| `checksum()` | `bytes` | コンテンツの SHA-256 チェックサム |
| `size()` | `int` | コンテンツのバイト数 |
| `data_chunk_count(chunk_size)` | `int` | 転送に必要なチャンク数（デフォルト: 1MB チャンク） |
| `read_at(offset, length)` | `bytes` | 指定オフセットからデータを読み取る |
| `encrypted()` | `bool` | 暗号化されたパックかどうか |

### クラスメソッド

#### `Pack.read_path(path)`

```python
@classmethod
def read_path(cls, path: str | Path) -> Pack
```

ファイルパスからリソースパックを読み込む。ZIP ファイルまたはディレクトリの両方に対応。

- **ZIP ファイル**: そのまま読み込み、`manifest.json` を解析
- **ディレクトリ**: ZIP アーカイブを作成してから読み込み

#### `Pack.read_bytes(data)`

```python
@classmethod
def read_bytes(cls, data: bytes) -> Pack
```

ZIP バイト列からリソースパックを読み込む。

---

## Manifest クラス

```python
from mcbe.resource.manifest import Manifest
```

`manifest.json` の解析結果を表すクラス。

### フィールド

| フィールド | 型 | 説明 |
|---|---|---|
| `format_version` | `int` | フォーマットバージョン（デフォルト: 2） |
| `header` | `Header` | パックヘッダー |
| `modules` | `list[Module]` | モジュールリスト |
| `dependencies` | `list[Dependency]` | 依存関係リスト |
| `capabilities` | `list[str]` | 必要な機能リスト |
| `metadata` | `Metadata` | メタデータ |

### メソッド

| メソッド | 戻り値 | 説明 |
|---|---|---|
| `Manifest.from_json(data)` | `Manifest` | 辞書から生成 |
| `Manifest.parse(json_str)` | `Manifest` | JSON 文字列から解析 |
| `has_scripts()` | `bool` | `client_data` モジュールを含むか |
| `has_textures()` | `bool` | `resources` モジュールを含むか |
| `has_behaviours()` | `bool` | `data` モジュールを含むか |
| `has_world_template()` | `bool` | `world_template` モジュールを含むか |

---

## Header クラス

```python
@dataclass
class Header:
    name: str = ""
    description: str = ""
    uuid: str = ""
    version: Version = Version()
    min_engine_version: Version = Version()
```

---

## Module クラス

```python
@dataclass
class Module:
    uuid: str = ""
    description: str = ""
    type: str = ""     # "resources", "data", "client_data", "world_template"
    version: Version = Version()
```

---

## Dependency クラス

```python
@dataclass
class Dependency:
    uuid: str = ""
    version: Version = Version()
```

---

## Version クラス

```python
@dataclass
class Version:
    major: int = 0
    minor: int = 0
    patch: int = 0
```

`str(version)` で `"1.0.0"` 形式の文字列を返す。

`Version.from_json(data)` は配列 (`[1, 0, 0]`) または文字列 (`"1.0.0"`) の両方をパースできる。
