FROM python:3.11-slim

# システム依存関係のインストール（FFmpeg含む）
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ設定
WORKDIR /app

# 依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY . .

# ポート公開
EXPOSE 5000

# 一時ディレクトリの作成（動画処理用）
RUN mkdir -p /tmp/video-analysis

# Gunicornで起動（本番環境用）
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "300", "--workers", "2", "app:app"]
