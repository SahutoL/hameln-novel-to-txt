# flask-novel-to-txt

## 概要
`flask-novel-to-txt` は、web 小説投稿サイト「ハーメルン」における小説本文をtxtファイルへ変換するPWA対応のツールです。

## サイト
[こちら](https://flask-novel-to-txt.onrender.com)から実際のサイトを訪れることができます。

## インストール
このリポジトリをクローンし、必要なパッケージをインストールしてください。

```bash
git clone https://github.com/SahutoL/flask-novel-to-txt.git
cd flask-novel-to-txt
pip install -r requirements.txt
```

## 使用方法
プロジェクトを実行するには以下のコマンドを実行してください。

```bash
uvicorn app:app --reload
```

サーバーが起動したら、ブラウザで http://127.0.0.1:5000/ にアクセスすることで確認できます。