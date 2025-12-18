# 🎬 AI Video Analyzer - 動画分析ツール

AI（GPT-4o Vision）を使って動画を自動分析し、バズらせるための編集アドバイスを提供するWebアプリケーションです。

## ✨ 機能

- 📹 動画アップロード（ドラッグ&ドロップ対応）
- 🔍 1秒ごとのフレーム自動分析
- 🎯 動画ジャンルの自動判定
- 📊 A/B/C/Dパート別のサマリー生成
- 🚀 バズらせるための7つの編集アドバイス
- 📄 PDF保存（ブラウザ印刷機能）
- 💅 モダンなUI（Tailwind CSS）

## 🌐 デモ

Renderにデプロイ済み: [あなたのRender URL]

## 🚀 Renderへのデプロイ方法

### 1. GitHubにプッシュ

```bash
git init
git add .
git commit -m "Initial commit for Render deployment"
git remote add origin https://github.com/yourusername/video-analyzer.git
git push -u origin main
```

### 2. Renderでデプロイ

1. [Render.com](https://render.com) にアクセス
2. **New** → **Web Service** を選択
3. GitHubリポジトリを接続
4. 以下を設定：
   - **Name**: `video-analyzer`（任意）
   - **Environment**: `Docker`
   - **Plan**: Free または有料プラン

5. **Environment Variables** に以下を追加：
   ```
   OPENAI_API_KEY=sk-proj-your-actual-api-key-here
   ```

6. **Create Web Service** をクリック

### 3. デプロイ完了

- 自動的にビルド→デプロイが開始されます
- 完了すると `https://video-analyzer-xxxx.onrender.com` のようなURLが発行されます

## 💻 ローカル開発

### 必要要件

- Python 3.11以上
- FFmpeg
- OpenAI APIキー

### セットアップ

1. **リポジトリをクローン**
   ```bash
   git clone https://github.com/yourusername/video-analyzer.git
   cd video-analyzer
   ```

2. **依存関係をインストール**
   ```bash
   pip install -r requirements.txt
   ```

3. **FFmpegをインストール**
   
   **Mac:**
   ```bash
   brew install ffmpeg
   ```
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt-get update
   sudo apt-get install ffmpeg
   ```
   
   **Windows:**
   - [FFmpeg公式サイト](https://ffmpeg.org/download.html)からダウンロード
   - 環境変数PATHに追加

4. **環境変数を設定**
   
   `.env` ファイルを作成：
   ```
   OPENAI_API_KEY=sk-proj-your-api-key-here
   ```

5. **アプリケーション起動**
   ```bash
   python app.py
   ```

6. **ブラウザでアクセス**
   ```
   http://localhost:5000
   ```

## 🐳 Docker での実行

```bash
# イメージをビルド
docker build -t video-analyzer .

# コンテナを起動
docker run -p 5000:5000 -e OPENAI_API_KEY=your-key-here video-analyzer
```

## 📁 プロジェクト構成

```
video-analyzer/
├── app.py                    # メインアプリケーション
├── requirements.txt          # Python依存関係
├── Dockerfile               # Docker設定
├── .gitignore
├── README.md
└── templates/
    ├── index.html          # メインページ
    └── pdf_template.html   # PDFテンプレート
```

## 🔧 技術スタック

- **Backend**: Flask 3.0
- **AI**: OpenAI GPT-4o (Vision + Text)
- **動画処理**: FFmpeg
- **Frontend**: Tailwind CSS + Vanilla JavaScript
- **デプロイ**: Docker + Render

## ⚙️ 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI APIキー | ✅ |
| `PORT` | ポート番号（Renderが自動設定） | ❌ |
| `SECRET_KEY` | Flask セッション秘密鍵（自動生成） | ❌ |

## ⚠️ 注意事項

- **動画サイズ**: 最大100MB
- **対応形式**: MP4, MOV, AVI, WebM
- **処理時間**: 1分動画で約1-3分
- **OpenAI API使用量**: 1分動画で約$0.50-1.00
- **Render Freeプラン**: 15分後にスリープ（初回アクセス時に起動）

## 📄 PDF保存方法

ブラウザの印刷機能を使用：

1. 分析結果画面で `Ctrl+P` (Mac: `Cmd+P`) を押す
2. プリンター選択で「**PDFとして保存**」を選択
3. 保存先を指定して保存

## 🛠️ トラブルシューティング

### Renderでデプロイに失敗する

- **ログを確認**: Renderダッシュボードの「Logs」タブ
- **環境変数**: `OPENAI_API_KEY` が正しく設定されているか確認
- **ビルドログ**: Dockerビルドエラーがないか確認

### OpenAI APIエラー

- APIキーが正しいか確認
- APIクォータ（使用量制限）を確認
- [OpenAI Platform](https://platform.openai.com/account/usage)

### FFmpegエラー

- FFmpegがインストールされているか確認
- `ffmpeg -version` でバージョン確認

## 🤝 貢献

プルリクエスト歓迎です！

1. Fork する
2. Feature ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. Commit する (`git commit -m 'Add amazing feature'`)
4. Push する (`git push origin feature/amazing-feature`)
5. Pull Request を作成

## 📝 ライセンス

MIT License

## 📧 お問い合わせ

質問や問題があれば Issue を作成してください。

---

Made with ❤️ using GPT-4o Vision
