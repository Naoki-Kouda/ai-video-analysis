#!/usr/bin/env python3
"""
動画分析ツール - Flaskアプリケーション
Render対応版（デバッグ強化 + 遅延初期化 + ヘルスチェック）
"""

from flask import Flask, request, render_template, jsonify, session
from openai import OpenAI
import os
import httpx
import sys
import base64
import subprocess
import tempfile
import shutil
from pathlib import Path
import secrets
from datetime import datetime
import re

# WeasyPrintは無効（ブラウザ印刷で代用）
WEASYPRINT_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(16))
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB制限

# OpenAI クライアント（Gunicornワーカーごとにメモリ独立）
client = None
last_openai_init_error = None


def _sanitize_api_key(raw: str) -> str:
    """
    APIキー文字列を安全に正規化：
    - 前後の空白/BOM除去
    - 両端のクォート除去（"sk-..." や 'sk-...' 対策）
    - 文字列中の改行/タブ等の空白類を除去（混入対策）
    """
    if raw is None:
        return ""
    s = raw.strip("\ufeff\r\n\t ")
    # 両端がクォートなら剥がす
    if (len(s) >= 2) and ((s[0] == s[-1]) and s[0] in ("'", '"')):
        s = s[1:-1]
    # 中に紛れた空白類を除去
    s = re.sub(r"\s+", "", s)
    return s


def get_api_key() -> str:
    """環境変数 → （ローカルのみ）.env の順で読む"""
    raw = os.environ.get("OPENAI_API_KEY", "")
    api_key = _sanitize_api_key(raw)

    # ローカル開発時のみ .env を読む（Renderでは不要）
    if not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            raw2 = os.environ.get("OPENAI_API_KEY", "")
            api_key = _sanitize_api_key(raw2)
            if api_key:
                print("✅ .envファイルから環境変数を読み込みました")
        except ImportError:
            pass

    return api_key


def init_openai(force: bool = False) -> bool:
    """OpenAI クライアントを初期化（デバッグ強化版）"""
    global client, last_openai_init_error

    if client is not None and not force:
        return True

    api_key = get_api_key()

    # デバッグ情報（キー本体は出さない）
    if api_key:
        head = api_key[:12]
        tail = api_key[-4:]
        print(f"🔑 OPENAI_API_KEY検出: len={len(api_key)} head={head}...tail={tail}")
    else:
        print("❌ OPENAI_API_KEYが空です（未設定 or 読み込み失敗）")
        last_openai_init_error = "OPENAI_API_KEY is empty"
        client = None
        return False

    # 形式チェック（緩め：sk- で始まるかだけ）
    if not api_key.startswith("sk-"):
        print("❌ APIキー形式が不正です（sk-で始まっていません）")
        last_openai_init_error = "API key does not start with 'sk-'"
        client = None
        return False

    try:
        client = OpenAI(api_key=api_key,http_client=httpx.Client(timeout=60.0),)
        last_openai_init_error = None
        print("✅ OpenAI クライアント初期化成功")
        return True
    except Exception as e:
        client = None
        last_openai_init_error = f"{type(e).__name__}: {e}"
        print(f"❌ OpenAI初期化エラー: {last_openai_init_error}")
        import traceback
        traceback.print_exc()
        return False


def extract_frames(video_path, output_dir, interval=1.0):
    """FFmpegで動画からフレーム抽出"""
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"fps=1/{interval}",
        "-q:v", "2",
        f"{output_dir}/frame_%04d.jpg",
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def encode_image_to_base64(image_path):
    """画像をbase64エンコード"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_frame(image_path, frame_number, interval):
    """OpenAI Visionでフレームを分析"""
    timestamp = frame_number * interval
    minutes = int(timestamp // 60)
    seconds = timestamp % 60
    time_str = f"{minutes:02d}:{seconds:04.1f}"

    base64_image = encode_image_to_base64(image_path)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "この画像を分析して、以下の形式で1行で簡潔に答えてください：\n内容: [何が映っているか] | テキスト: [画像内のテキスト、なければ「なし」]"
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
            max_tokens=100,
        )

        result = response.choices[0].message.content.strip()
        return {"timestamp": time_str, "time_seconds": timestamp, "content": result}

    except Exception as e:
        return {"timestamp": time_str, "time_seconds": timestamp, "content": f"エラー: {str(e)}"}


def generate_final_report(frame_results):
    """全フレームから最終レポート生成"""
    frames_summary = "\n".join([f"{r['timestamp']} | {r['content']}" for r in frame_results])
    total_duration = frame_results[-1]["time_seconds"] if frame_results else 0

    prompt = f"""以下は動画の各フレーム分析結果です（総尺: {total_duration:.1f}秒）：

{frames_summary}

この動画を分析して、以下の形式でJSON形式で回答してください：

{{
  "genre": "動画のジャンル（例: ビジネス解説系、Vlog、ゲーム実況など）",
  "genre_confidence": "判定の信頼度（パーセント、数値のみ）",
  "genre_reason": "このジャンルと判定した理由（1-2文）",
  "parts": [
    {{"name": "Aパート", "timerange": "0:00-0:15", "summary": "このパートの内容要約"}},
    {{"name": "Bパート", "timerange": "0:15-0:30", "summary": "このパートの内容要約"}},
    {{"name": "Cパート", "timerange": "0:30-0:45", "summary": "このパートの内容要約"}},
    {{"name": "Dパート", "timerange": "0:45-1:00", "summary": "このパートの内容要約"}}
  ],
  "advice": [
    {{"title": "1. カット編集", "content": "具体的なアドバイス（4-6行程度）"}},
    {{"title": "2. テロップ戦略", "content": "具体的なアドバイス"}},
    {{"title": "3. BGM・効果音", "content": "具体的なアドバイス"}},
    {{"title": "4. 視覚効果", "content": "具体的なアドバイス"}},
    {{"title": "5. サムネイル設計", "content": "具体的なアドバイス"}},
    {{"title": "6. 構成の改善", "content": "具体的なアドバイス"}},
    {{"title": "7. トレンド対応", "content": "このジャンルの最新トレンド"}}
  ]
}}

動画を4つのパートに均等分割して、各パートの内容をまとめてください。
編集アドバイスは、このジャンルに特化した実践的で具体的な内容にしてください。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )
        import json
        return json.loads(response.choices[0].message.content)

    except Exception as e:
        return {
            "genre": "エラー",
            "genre_confidence": "0",
            "genre_reason": f"分析中にエラーが発生しました: {str(e)}",
            "parts": [],
            "advice": [],
        }


@app.route("/")
def index():
    return render_template("index.html", weasyprint_available=WEASYPRINT_AVAILABLE)


@app.route("/healthz")
def healthz():
    """Renderログ以外でも最低限の状態確認ができるように"""
    ffmpeg_ok = True
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        ffmpeg_ok = False

    api_key = get_api_key()
    return jsonify({
        "ok": True,
        "client_ready": client is not None,
        "api_key_present": bool(api_key),
        "api_key_len": len(api_key) if api_key else 0,
        "last_openai_init_error": last_openai_init_error,
        "ffmpeg_ok": ffmpeg_ok,
    })


@app.route("/analyze", methods=["POST"])
def analyze():
    """動画分析のメインエンドポイント（遅延初期化）"""
    # ここで毎回「未初期化なら初期化」を試す（Renderの再起動/環境変数反映漏れに強くなる）
    if client is None:
        init_openai()

    if client is None:
        # デバッグしやすいように原因も返す（本番で出したくなければ削ってOK）
        return jsonify({
            "error": "OpenAI APIキーが設定されていません（または初期化に失敗しました）",
            "detail": last_openai_init_error
        }), 500

    if "video" not in request.files:
        return jsonify({"error": "動画ファイルが選択されていません"}), 400

    video = request.files["video"]
    if video.filename == "":
        return jsonify({"error": "動画ファイルが選択されていません"}), 400

    temp_dir = tempfile.mkdtemp()
    frames_dir = tempfile.mkdtemp()

    try:
        video_path = os.path.join(temp_dir, "video.mp4")
        video.save(video_path)
        print(f"📹 動画を保存: {video_path}")

        print("🎞️ フレーム抽出中...")
        extract_frames(video_path, frames_dir, interval=1.0)

        frames = sorted(Path(frames_dir).glob("frame_*.jpg"))
        if not frames:
            return jsonify({"error": "フレームが抽出できませんでした"}), 500

        print(f"✅ {len(frames)}フレームを抽出")
        print("🔍 フレーム分析中...")

        frame_results = []
        for i, frame_path in enumerate(frames, start=1):
            print(f"  - {i}/{len(frames)} フレーム処理中...")
            result = analyze_frame(str(frame_path), i, 1.0)
            frame_results.append(result)

        print("✅ フレーム分析完了")
        print("📊 最終レポート生成中...")
        final_report = generate_final_report(frame_results)

        session["last_report"] = final_report
        session["analysis_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print("✅ 分析完了")
        return jsonify({"success": True, "total_frames": len(frames), "report": final_report})

    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(frames_dir, ignore_errors=True)


@app.route("/pdf")
def download_pdf():
    # 既存の案内ページのままでOK
    return """
    <html><head><meta charset="UTF-8"></head>
    <body style="font-family:sans-serif;padding:24px;">
      <h1>PDF保存方法</h1>
      <p>ブラウザの印刷機能を使用してPDFとして保存できます。</p>
      <ol>
        <li>分析結果画面で Ctrl+P (Mac: Cmd+P)</li>
        <li>プリンター選択で「PDFとして保存」</li>
        <li>保存</li>
      </ol>
      <p><a href="/">ホームに戻る</a></p>
    </body></html>
    """


# ========================================
# Gunicorn起動時に一度初期化を試す
# ========================================
print("\n" + "=" * 60)
print("🚀 アプリケーション初期化")
print("=" * 60)

init_success = init_openai()

print("=" * 60 + "\n")
if not init_success:
    print("⚠️ 警告：OpenAI初期化に失敗しました（/analyzeで再試行します）")
    print(f"   理由: {last_openai_init_error}")


if __name__ == "__main__":
    # ローカル開発サーバー起動
    if client is None:
        print("⚠️ OpenAI未初期化のまま起動します（/analyzeで再試行）")

    port = int(os.environ.get("PORT", 5000))
    print(f"\n🚀 サーバー起動: http://0.0.0.0:{port}")
    print("=" * 60 + "\n")
    app.run(debug=False, host="0.0.0.0", port=port)