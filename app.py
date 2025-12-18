#!/usr/bin/env python3
"""
動画分析ツール - Flaskアプリケーション
Render対応版（修正版 v2）
"""

from flask import Flask, request, render_template, jsonify, session, send_file
from openai import OpenAI
import os
import sys
import base64
import subprocess
import tempfile
import shutil
from pathlib import Path
import secrets
from datetime import datetime
import io

# ===== 環境変数の読み込み =====
# Render環境では環境変数から直接読み込む
api_key = os.environ.get('OPENAI_API_KEY', '').strip()

# ローカル開発時のみ.envから読む
if not api_key:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get('OPENAI_API_KEY', '').strip()
        print("✅ .envファイルから環境変数を読み込みました")
    except ImportError:
        pass

if api_key:
    # 前後の空白・改行・制御文字を完全除去
    api_key = api_key.strip('\ufeff\r\n\t ')
    os.environ['OPENAI_API_KEY'] = api_key
    print(f"✅ APIキー検出: {api_key[:20]}...{api_key[-4:]}")
else:
    print("⚠️ OPENAI_API_KEYが設定されていません")

# WeasyPrintは無効（ブラウザ印刷で代用）
WEASYPRINT_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB制限

# OpenAI クライアント初期化
client = None

def init_openai():
    """OpenAI クライアントを初期化"""
    global client
    api_key = os.environ.get('OPENAI_API_KEY', '').strip()
    
    if not api_key:
        print("❌ エラー: OPENAI_API_KEYが設定されていません")
        return False
    
    if not api_key.startswith('sk-'):
        print(f"❌ エラー: APIキーの形式が不正です")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI クライアント初期化成功")
        return True
    except Exception as e:
        print(f"❌ OpenAI初期化エラー: {e}")
        return False

def extract_frames(video_path, output_dir, interval=1.0):
    """
    FFmpegで動画からフレームを抽出
    
    Args:
        video_path: 動画ファイルのパス
        output_dir: 出力ディレクトリ
        interval: 抽出間隔(秒) - デフォルト1秒
    """
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vf', f'fps=1/{interval}',
        '-q:v', '2',
        f'{output_dir}/frame_%04d.jpg'
    ]
    
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def encode_image_to_base64(image_path):
    """画像をbase64エンコード"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def analyze_frame(image_path, frame_number, interval):
    """
    OpenAI Vision APIでフレームを分析
    
    Args:
        image_path: 画像ファイルのパス
        frame_number: フレーム番号
        interval: フレーム間隔
    
    Returns:
        分析結果の辞書
    """
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
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=100
        )
        
        result = response.choices[0].message.content.strip()
        return {
            'timestamp': time_str,
            'time_seconds': timestamp,
            'content': result
        }
    
    except Exception as e:
        return {
            'timestamp': time_str,
            'time_seconds': timestamp,
            'content': f"エラー: {str(e)}"
        }

def generate_final_report(frame_results):
    """
    全フレーム分析結果から最終レポートを生成
    
    Args:
        frame_results: フレーム分析結果のリスト
    
    Returns:
        最終レポートの辞書
    """
    # 全フレーム結果をテキストにまとめる
    frames_summary = "\n".join([
        f"{r['timestamp']} | {r['content']}" 
        for r in frame_results
    ])
    
    # 動画の総尺を計算
    total_duration = frame_results[-1]['time_seconds'] if frame_results else 0
    
    # GPTに最終分析を依頼
    prompt = f"""以下は動画の各フレーム分析結果です（総尺: {total_duration:.1f}秒）：

{frames_summary}

この動画を分析して、以下の形式でJSON形式で回答してください：

{{
  "genre": "動画のジャンル（例: ビジネス解説系、Vlog、ゲーム実況など）",
  "genre_confidence": "判定の信頼度（パーセント、数値のみ）",
  "genre_reason": "このジャンルと判定した理由（1-2文）",
  "parts": [
    {{
      "name": "Aパート",
      "timerange": "0:00-0:15",
      "summary": "このパートの内容要約"
    }},
    {{
      "name": "Bパート",
      "timerange": "0:15-0:30",
      "summary": "このパートの内容要約"
    }},
    {{
      "name": "Cパート",
      "timerange": "0:30-0:45",
      "summary": "このパートの内容要約"
    }},
    {{
      "name": "Dパート",
      "timerange": "0:45-1:00",
      "summary": "このパートの内容要約"
    }}
  ],
  "advice": [
    {{
      "title": "1. カット編集",
      "content": "具体的なアドバイス（4-6行程度）"
    }},
    {{
      "title": "2. テロップ戦略",
      "content": "具体的なアドバイス"
    }},
    {{
      "title": "3. BGM・効果音",
      "content": "具体的なアドバイス"
    }},
    {{
      "title": "4. 視覚効果",
      "content": "具体的なアドバイス"
    }},
    {{
      "title": "5. サムネイル設計",
      "content": "具体的なアドバイス"
    }},
    {{
      "title": "6. 構成の改善",
      "content": "具体的なアドバイス"
    }},
    {{
      "title": "7. トレンド対応",
      "content": "このジャンルの最新トレンド"
    }}
  ]
}}

動画を4つのパートに均等分割して、各パートの内容をまとめてください。
編集アドバイスは、このジャンルに特化した実践的で具体的な内容にしてください。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=2000
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        return {
            "genre": "エラー",
            "genre_confidence": "0",
            "genre_reason": f"分析中にエラーが発生しました: {str(e)}",
            "parts": [],
            "advice": []
        }

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html', weasyprint_available=WEASYPRINT_AVAILABLE)

@app.route('/analyze', methods=['POST'])
def analyze():
    """動画分析のメインエンドポイント"""
    
    if not client:
        return jsonify({'error': 'OpenAI APIキーが設定されていません'}), 500
    
    if 'video' not in request.files:
        return jsonify({'error': '動画ファイルが選択されていません'}), 400
    
    video = request.files['video']
    
    if video.filename == '':
        return jsonify({'error': '動画ファイルが選択されていません'}), 400
    
    # 一時ディレクトリ作成
    temp_dir = tempfile.mkdtemp()
    frames_dir = tempfile.mkdtemp()
    
    try:
        # 動画を一時保存
        video_path = os.path.join(temp_dir, 'video.mp4')
        video.save(video_path)
        
        print(f"📹 動画を保存: {video_path}")
        
        # フレーム抽出
        print("🎞️ フレーム抽出中...")
        extract_frames(video_path, frames_dir, interval=1.0)
        
        # 抽出されたフレーム一覧
        frames = sorted(Path(frames_dir).glob('frame_*.jpg'))
        
        if not frames:
            return jsonify({'error': 'フレームが抽出できませんでした'}), 500
        
        print(f"✅ {len(frames)}フレームを抽出")
        
        # 各フレームを分析
        frame_results = []
        print("🔍 フレーム分析中...")
        
        for i, frame_path in enumerate(frames, start=1):
            print(f"  - {i}/{len(frames)} フレーム処理中...")
            result = analyze_frame(frame_path, i, 1.0)
            frame_results.append(result)
        
        print("✅ フレーム分析完了")
        
        # 最終レポート生成
        print("📊 最終レポート生成中...")
        final_report = generate_final_report(frame_results)
        
        # セッションに保存（PDF生成用）
        session['last_report'] = final_report
        session['analysis_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print("✅ 分析完了")
        
        return jsonify({
            'success': True,
            'total_frames': len(frames),
            'report': final_report
        })
    
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
    finally:
        # クリーンアップ
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(frames_dir, ignore_errors=True)

@app.route('/pdf')
def download_pdf():
    """PDF生成・ダウンロード（ブラウザ印刷を案内）"""
    return """
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: 'Hiragino Sans', 'Yu Gothic', sans-serif;
                padding: 50px;
                text-align: center;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: white;
                color: #333;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                max-width: 600px;
            }
            h1 { color: #667eea; margin-bottom: 20px; }
            p { line-height: 1.8; margin: 15px 0; }
            .steps {
                text-align: left;
                background: #f5f5f5;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }
            .steps li { margin: 10px 0; }
            a {
                display: inline-block;
                margin-top: 20px;
                text-decoration: none;
                background: #667eea;
                color: white;
                padding: 15px 30px;
                border-radius: 5px;
                transition: all 0.3s;
            }
            a:hover { background: #764ba2; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📄 PDF保存方法</h1>
            <p>ブラウザの印刷機能を使用してPDFとして保存できます。</p>
            <div class="steps">
                <ol>
                    <li>分析結果画面で <strong>Ctrl+P</strong> (Mac: <strong>Cmd+P</strong>) を押す</li>
                    <li>プリンター選択で「<strong>PDFとして保存</strong>」を選択</li>
                    <li>保存先を指定して保存</li>
                </ol>
            </div>
            <a href="/">🏠 ホームに戻る</a>
        </div>
    </body>
    </html>
    """

# ========================================
# ★★★ 最重要：Gunicorn対応の初期化 ★★★
# ========================================
print("\n" + "=" * 60)
print("🚀 アプリケーション初期化開始")
print("=" * 60)

# OpenAIクライアントを初期化（Gunicorn起動時も必ず実行）
if init_openai():
    print("✅ 初期化完了：アプリケーションは正常に起動しました")
else:
    print("⚠️ 警告：OpenAI APIキーが設定されていません")
    print("   環境変数 OPENAI_API_KEY を確認してください")

print("=" * 60 + "\n")

# ========================================
# ローカル開発サーバー起動
# ========================================
if __name__ == '__main__':
    # ローカル開発時のチェック
    if not client:
        print("❌ エラー: OpenAI APIキーの設定に問題があります")
        print("環境変数 OPENAI_API_KEY を設定してください")
        sys.exit(1)
    
    # FFmpegの確認
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        print("✅ FFmpeg が利用可能です")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpegが見つかりません")
        sys.exit(1)
    
    # ポート設定（Render対応）
    port = int(os.environ.get('PORT', 5000))
    
    print(f"\n🚀 サーバー起動: http://0.0.0.0:{port}")
    print("=" * 60 + "\n")
    
    app.run(debug=False, host='0.0.0.0', port=port)
