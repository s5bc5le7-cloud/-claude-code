# せどりツール

Amazon商品検索・利益計算Webアプリ

## セットアップ

```bash
# 1. ライブラリをインストール
pip3 install -r requirements.txt

# 2. APIキーを設定
open .env   # Mac
# または: nano .env / code .env

# 3. サーバーを起動
python3 app.py
```

ブラウザで http://localhost:5000 を開く。

## APIキーの取得

Amazon PA-API v5 を使用します。

1. [Amazonアソシエイト](https://affiliate.amazon.co.jp/) に登録
2. [認証情報の管理](https://affiliate-program.amazon.co.jp/assoc_credentials/home) でアクセスキーを発行
3. `.env` に貼り付け

> **APIキー未設定でも動作します**（デモデータが表示されます）

## 機能

| 機能 | 説明 |
|------|------|
| 商品検索 | キーワードでAmazon商品を検索 |
| 利益計算 | 仕入れ値・売値から利益とROIを自動計算 |
| 手数料内訳 | 紹介料・Amazon手数料・FBA手数料を表示 |

## 手数料の計算式

```
利益 = 売値 - 仕入れ値 - 紹介料(10%) - Amazon手数料(8%) - FBA発送手数料(500円)
ROI  = 利益 ÷ 仕入れ値 × 100
```

※手数料はカテゴリや商品サイズにより異なります。目安としてご利用ください。
