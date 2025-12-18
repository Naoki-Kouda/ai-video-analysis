#!/bin/bash

echo "=================================="
echo "🧪 ローカル環境テスト"
echo "=================================="
echo ""

# Python バージョン確認
echo "📌 Python バージョン:"
python --version || python3 --version
echo ""

# FFmpeg 確認
echo "📌 FFmpeg チェック:"
if command -v ffmpeg &> /dev/null; then
    ffmpeg -version | head -1
    echo "✅ FFmpeg が利用可能です"
else
    echo "❌ FFmpeg が見つかりません"
    echo "   インストールしてください: brew install ffmpeg"
    exit 1
fi
echo ""

# 依存関係インストール
echo "📦 依存関係をインストール中..."
pip install -r requirements.txt
echo ""

# 環境変数チェック
echo "🔑 環境変数チェック:"
if [ -f .env ]; then
    echo "✅ .env ファイルが見つかりました"
    if grep -q "OPENAI_API_KEY=sk-" .env; then
        echo "✅ OPENAI_API_KEY が設定されています"
    else
        echo "⚠️ OPENAI_API_KEY を.envファイルに設定してください"
        echo "   例: OPENAI_API_KEY=sk-proj-your-key-here"
    fi
else
    echo "⚠️ .envファイルが見つかりません"
    echo "   .env.example をコピーして .env を作成してください"
    echo "   cp .env.example .env"
fi
echo ""

# Dockerテスト（オプション）
echo "🐳 Docker チェック（オプション）:"
if command -v docker &> /dev/null; then
    echo "✅ Docker が利用可能です"
    echo "   ビルドテスト: docker build -t video-analyzer-test ."
else
    echo "⚠️ Docker が見つかりません（必須ではありません）"
fi
echo ""

echo "=================================="
echo "✅ テスト完了！"
echo "=================================="
echo ""
echo "次のステップ:"
echo "1. .env ファイルに OPENAI_API_KEY を設定"
echo "2. python app.py でアプリを起動"
echo "3. http://localhost:5000 にアクセス"
echo ""
