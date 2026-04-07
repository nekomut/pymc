# テキストフォーマット

`mcbe.text.formatting` モジュールは、Minecraft Bedrock Edition のテキスト装飾コード（`\u00a7` コード）、ANSI 変換、HTML スタイルのフォーマットを提供する。

---

## カラー定数

| 定数 | コード | 色 |
|---|---|---|
| `BLACK` | `\u00a70` | 黒 |
| `DARK_BLUE` | `\u00a71` | 暗い青 |
| `DARK_GREEN` | `\u00a72` | 暗い緑 |
| `DARK_AQUA` | `\u00a73` | 暗い水色 |
| `DARK_RED` | `\u00a74` | 暗い赤 |
| `DARK_PURPLE` | `\u00a75` | 暗い紫 |
| `ORANGE` | `\u00a76` | オレンジ |
| `GREY` | `\u00a77` | 灰色 |
| `DARK_GREY` | `\u00a78` | 暗い灰色 |
| `BLUE` | `\u00a79` | 青 |
| `GREEN` | `\u00a7a` | 緑 |
| `AQUA` | `\u00a7b` | 水色 |
| `RED` | `\u00a7c` | 赤 |
| `PURPLE` | `\u00a7d` | 紫 |
| `YELLOW` | `\u00a7e` | 黄色 |
| `WHITE` | `\u00a7f` | 白 |

### マテリアルカラー

| 定数 | コード | 色 |
|---|---|---|
| `DARK_YELLOW` | `\u00a7g` | 暗い黄色 |
| `QUARTZ` | `\u00a7h` | クォーツ |
| `IRON` | `\u00a7i` | 鉄 |
| `NETHERITE` | `\u00a7j` | ネザライト |
| `REDSTONE` | `\u00a7m` | レッドストーン |
| `COPPER` | `\u00a7n` | 銅 |
| `GOLD` | `\u00a7p` | 金 |
| `EMERALD` | `\u00a7q` | エメラルド |
| `DIAMOND` | `\u00a7s` | ダイヤモンド |
| `LAPIS` | `\u00a7t` | ラピスラズリ |
| `AMETHYST` | `\u00a7u` | アメジスト |
| `RESIN` | `\u00a7v` | レジン |

---

## スタイル定数

| 定数 | コード | 効果 |
|---|---|---|
| `OBFUSCATED` | `\u00a7k` | 難読化（文字がランダムに変化） |
| `BOLD` | `\u00a7l` | 太字 |
| `ITALIC` | `\u00a7o` | 斜体 |
| `RESET` | `\u00a7r` | リセット |

---

## 関数

### `to_ansi(text: str) -> str`

Minecraft のフォーマットコードを ANSI エスケープコードに変換する。ターミナルでの表示に使用する。

```python
from mcbe.text.formatting import to_ansi

text = "\u00a7cエラー\u00a7r: 何か問題が発生しました"
print(to_ansi(text))  # ターミナルで赤色表示
```

### `clean(text: str) -> str`

すべての Minecraft フォーマットコードを文字列から除去する。

```python
from mcbe.text.formatting import clean

text = "\u00a7a緑色\u00a7rのテキスト"
print(clean(text))  # "緑色のテキスト"
```

### `colourf(format_str: str) -> str`

HTML スタイルのタグを Minecraft フォーマットコードに変換する。

```python
from mcbe.text.formatting import colourf

text = colourf("<red>警告</red>: <bold>重要<bold>なメッセージ")
# → "\u00a7r\u00a7c警告\u00a7r: \u00a7l重要\u00a7r\u00a7lなメッセージ"
```

サポートされるタグ: `<black>`, `<dark-blue>`, `<dark-green>`, `<dark-aqua>`, `<dark-red>`, `<dark-purple>`, `<orange>`, `<grey>`, `<dark-grey>`, `<blue>`, `<green>`, `<aqua>`, `<red>`, `<purple>`, `<yellow>`, `<white>`, `<bold>` / `<b>`, `<italic>` / `<i>`, その他すべてのマテリアルカラー名。
