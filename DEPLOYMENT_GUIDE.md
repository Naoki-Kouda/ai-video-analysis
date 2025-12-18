# 🚀 Renderデプロイガイド

このプロジェクトはRenderへのデプロイに最適化されています。

## 📋 変更点サマリー

### 元のコードからの主な変更：

1. **✅ Dockerfile の作成**
   - Python 3.11-slim ベースイメージ
   - FFmpegをシステム依存関係としてインストール
   - Gunicornで本番環境起動

2. **✅ requirements.txt の修正**
   - `weasyprint`を削除（ビルドエラー防止）
   - ブラウザの印刷機能でPDF保存に対応
   - 必要最小限の依存関係のみ

3. **✅ app.py の修正**
   - 環境変数の読み込みをシンプル化
   - Render環境に対応（`PORT`環境変数）
   - デバッグモードを無効化（本番環境対応）
   - PDF生成を無効化し、ブラウザ印刷を案内

4. **✅ 環境変数設定**
   - `.env.example`を作成（ローカル開発用）
   - Renderでは環境変数を直接設定

## 🎯 デプロイ手順

### Step 1: GitHubリポジトリの準備

```bash
# このフォルダで実行
cd video-analyzer-render

# Gitの初期化
git init

# ファイルを追加
git add .

# コミット
git commit -m "Initial commit for Render deployment"

# GitHubリポジトリを作成して接続
git remote add origin https://github.com/yourusername/video-analyzer.git
git branch -M main
git push -u origin main
```

### Step 2: Renderでのデプロイ

1. **Render.comにログイン**
   - https://render.com にアクセス
   - GitHubアカウントでサインアップ/ログイン

2. **New Web Service を作成**
   - ダッシュボードで「New」→「Web Service」をクリック
   - GitHubリポジトリを接続

3. **設定項目**
   
   | 項目 | 値 |
   |------|-----|
   | Name | `video-analyzer`（任意） |
   | Environment | **Docker** を選択 |
   | Region | Singapore（日本から近い） |
   | Branch | `main` |
   | Plan | **Free** または Starter |

4. **環境変数を設定**
   
   「Environment」セクションで「Add Environment Variable」をクリック：
   
   ```
   Key: OPENAI_API_KEY
   Value: sk-proj-your-actual-api-key-here
   ```
   
   ⚠️ **重要**: 自分のOpenAI APIキーに置き換えてください

5. **Create Web Service をクリック**

### Step 3: デプロイ完了を待つ

- ビルドログが表示されます
- 初回デプロイは5-10分程度かかります
- 成功すると緑色で「Live」と表示されます

### Step 4: アプリケーションにアクセス

- 発行されたURL（例: `https://video-analyzer-xxxx.onrender.com`）にアクセス
- 動画をアップロードして分析を開始！

## 🔧 トラブルシューティング

### ❌ Build Failed (ビルド失敗)

**原因**: Dockerfileの問題

**解決策**:
```bash
# ローカルでDockerビルドをテスト
docker build -t test-video-analyzer .
```

### ❌ Application Error (起動エラー)

**原因**: 環境変数が設定されていない

**解決策**:
1. Renderダッシュボード → Environment
2. `OPENAI_API_KEY` が正しく設定されているか確認
3. APIキーが `sk-` で始まっているか確認

### ❌ OpenAI API Error

**原因**: APIキーが無効 / クォータ超過

**解決策**:
1. https://platform.openai.com/account/api-keys でキーを確認
2. https://platform.openai.com/account/usage で使用量を確認
3. 必要に応じて支払い方法を追加

### ⏱️ アプリが遅い / 初回アクセスが遅い

**原因**: Freeプランでは15分後にスリープ

**対策**:
- 初回アクセス時に30秒〜1分待つ
- Starter プラン（$7/月）にアップグレードでスリープなし

## 📊 Freeプラン vs Starterプラン

| 項目 | Free | Starter ($7/月) |
|------|------|-----------------|
| スリープ | 15分後 | なし |
| ビルド時間 | 制限あり | 高速 |
| カスタムドメイン | ❌ | ✅ |
| おすすめ | テスト用 | 本番運用 |

## 🎨 カスタマイズ

### アプリ名を変更

`README.md`と`templates/index.html`のタイトル部分を編集

### UIカラーを変更

`templates/index.html`の`.gradient-bg`スタイルを編集

### 分析間隔を変更

`app.py`の`extract_frames()`関数の`interval`パラメータを変更

## 📝 次のステップ

- [ ] カスタムドメインを設定
- [ ] GitHub Actionsで自動デプロイ
- [ ] ログ監視とエラー通知
- [ ] パフォーマンス最適化

## 🆘 サポート

問題が発生した場合：

1. **Renderログを確認**: Dashboard → Logs
2. **GitHubでIssueを作成**
3. **Render Discordコミュニティ**: https://render.com/discord

---

Good luck with your deployment! 🚀
