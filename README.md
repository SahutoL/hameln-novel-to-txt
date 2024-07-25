# hameln-novel-to-txt

## 概要
`hameln-novel-to-txt` は、web 小説投稿サイト「ハーメルン」における小説本文をtxtファイルへ変換するPWA対応のツールです。

## サイト
[こちら](https://hameln-novel-to-txt.onrender.com)から実際のサイトを訪れることができます。

### 画像
<img src="https://github.com/user-attachments/assets/aa2bd87c-8286-4ced-aa1d-e7d51640c864" width="50%" height="50%" />
<img src="https://github.com/user-attachments/assets/fa0bca4d-235e-4fd2-b94f-4a2dbc5e7df3" width="50%" height="50%" />
<img src="https://github.com/user-attachments/assets/66719511-ddc6-44fa-ad56-b6c0af8eac09" width="50%" height="50%" />

## 機能

- ハーメルンの小説URLからテキストファイルを生成
- キーワードによる小説検索機能
- 検索結果から直接URLを入力フォームに反映
- PWA機能に対応

## 使用方法
### インストール
このリポジトリをクローンし、必要なパッケージをインストールしてください。

```bash
git clone https://github.com/SahutoL/hameln-novel-to-txt.git
cd hameln-novel-to-txt
python -m venv venv
. venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 起動方法
プロジェクトを実行するには以下のコマンドを実行してください。

```bash
uvicorn app:app --reload
```

サーバーが起動したら、ブラウザで `http://127.0.0.1:5000` にアクセスすることで確認できます。

### 使い方

1. ブラウザで `http://localhost:5000` にアクセスします。

2. 小説のURLを直接入力するか、検索機能を使用して小説を見つけます。

3. 「Download Novel」ボタンをクリックして、テキストファイルをダウンロードします。

## 注意事項

このツールは個人的な使用を目的としています。著作権法を遵守し、ダウンロードしたコンテンツの取り扱いには十分注意してください。

## ライセンス

このプロジェクトは [MIT ライセンス](LICENSE) のもとで公開されています。

## 貢献

プルリクエストは歓迎します。大きな変更を加える場合は、まずissueを開いて議論してください。

## 連絡先

質問や提案がある場合は、[Issues](https://github.com/SahutoL/hameln-novel-to-txt/issues)を開いてください。
