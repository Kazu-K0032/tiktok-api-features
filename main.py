import logging
import os
from flask import Flask
from app.config import Config
from app.views import Views
from app.utils import setup_logging, cleanup_caches

# モックデータセットアップの状態を管理
_mock_data_setup_done = False

def setup_mock_data_if_needed():
    """Vercelデプロイ時にモックデータをセットアップ（遅延実行）"""
    global _mock_data_setup_done

    if _mock_data_setup_done:
        return

    if os.getenv("IS_DEPLOY_SITE", "false").lower() == "true":
        try:
            from pathlib import Path
            import sys
            import importlib.util

            # subprocessの代わりに直接インポートして実行
            script_path = Path(__file__).parent / "scripts" / "setup_mock_data.py"
            if script_path.exists():
                # スクリプトを直接実行
                spec = importlib.util.spec_from_file_location("setup_mock_data", str(script_path))
                module = importlib.util.module_from_spec(spec)
                sys.modules["setup_mock_data"] = module
                spec.loader.exec_module(module)

                # main関数を実行
                if hasattr(module, 'main'):
                    # モックデータファイルの数をカウント（実行前）
                    mock_data_dir = Path(__file__).parent / "mock_data"
                    files_before = len(list(mock_data_dir.glob("*.json"))) if mock_data_dir.exists() else 0

                    module.main()

                    # モックデータファイルの数をカウント（実行後）
                    files_after = len(list(mock_data_dir.glob("*.json"))) if mock_data_dir.exists() else 0

                    # ファイルが実際に作成された場合のみログを出力
                    if files_after > files_before:
                        logging.info(f"モックデータのセットアップが完了しました ({files_after - files_before} ファイル作成)")
                    elif files_after == 0:
                        logging.warning("モックデータのセットアップを試行しましたが、ファイルが作成されませんでした（環境変数が設定されていない可能性があります）")
                    else:
                        logging.info("モックデータのセットアップを試行しました（既存ファイルを確認）")

                    _mock_data_setup_done = True
        except Exception as e:
            # エラーをログに出力するが、アプリは起動できるようにする
            logging.warning(f"モックデータのセットアップスキップ: {e}")
            import traceback
            logging.error(traceback.format_exc())
            _mock_data_setup_done = True  # 失敗しても再試行しない
    else:
        # IS_DEPLOY_SITEがfalseの場合はセットアップをスキップ
        _mock_data_setup_done = True

def create_app():
    """Flaskアプリケーションを作成"""
    try:
        # ログ設定を初期化
        setup_logging()

        app = Flask(__name__, static_folder='static', template_folder='templates')

        # 設定を適用
        config = Config()
        app.secret_key = "tiktok_api_secret_key_2024"  # セッション機能に必要

        # ビューコントローラーを初期化
        views = Views()

        # 最初のリクエスト時にモックデータをセットアップ（Flask 2.2以降の対応）
        first_request_done = {'done': False}

        @app.before_request
        def handle_before_request():
            """リクエスト前処理（モックデータセットアップ + キャッシュクリーンアップ）"""
            # 最初のリクエスト時にモックデータをセットアップ
            if not first_request_done['done']:
                try:
                    setup_mock_data_if_needed()
                    first_request_done['done'] = True
                except Exception as e:
                    logging.warning(f"モックデータセットアップエラー（無視して継続）: {e}")
                    first_request_done['done'] = True

            # リクエストの10%でキャッシュクリーンアップを実行
            import random
            if random.random() < 0.1:
                cleanup_caches()

        # モックデータのセットアップは最初のリクエスト時に実行される（ここでは試行しない）
        # これにより、アプリケーションの起動をブロックしない

        # ルートを登録
        @app.route("/")
        def index():
            return views.index()

        @app.route("/login")
        def login():
            return views.login()

        @app.route("/callback/")
        def callback():
            return views.callback()

        @app.route("/dashboard")
        def dashboard():
            return views.dashboard()

        @app.route("/video/<video_id>")
        def video_detail(video_id):
            return views.video_detail(video_id)

        @app.route("/logout")
        def logout():
            return views.logout()

        # API エンドポイント
        @app.route("/api/switch-user", methods=["POST"])
        def api_switch_user():
            return views.api_switch_user()

        @app.route("/api/remove-user", methods=["POST"])
        def api_remove_user():
            return views.api_remove_user()

        @app.route("/api/user-data")
        def api_get_user_data():
            return views.api_get_user_data()

        @app.route("/api/users")
        def api_get_users():
            return views.api_get_users()

        @app.route("/debug/session")
        def debug_session():
            return views.debug_session()

        @app.route("/upload")
        def video_upload():
            return views.video_upload()

        @app.route("/api/upload-video", methods=["POST"])
        def api_upload_video():
            return views.api_upload_video()

        @app.route("/api/upload-draft", methods=["POST"])
        def api_upload_draft():
            return views.api_upload_draft()

        # ファビコン用のルート（ブラウザが自動的に探す）
        @app.route("/favicon.ico")
        def favicon():
            return app.send_static_file("images/favicon.svg")

        return app

    except Exception as e:
        logging.error(f"アプリケーション作成エラー: {e}")
        import traceback
        logging.error(traceback.format_exc())
        # エラーが発生しても最小限のアプリを返す
        app = Flask(__name__)
        app.secret_key = "tiktok_api_secret_key_2024"

        @app.route("/")
        def error_handler():
            import traceback
            error_detail = traceback.format_exc()
            return f"Application Error: {str(e)}\n\n{error_detail}", 500

        return app

# Vercel用にapp変数をエクスポート（重要！）
app = create_app()

# ローカル実行用
if __name__ == "__main__":
    # source venv/bin/activate
    # python main.py
    from dotenv import load_dotenv
    from app.utils import get_app_port
    import os

    # 環境変数を読み込み
    load_dotenv()

    # ポートを取得
    port = get_app_port()

    # Flaskのリローダーで親プロセスの場合のみメッセージを表示（重複を防ぐ）
    # 環境変数WERKZEUG_RUN_MAINが設定されていない場合のみ表示
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print(f"ローカルアクセス: http://127.0.0.1:{port}")

        if os.getenv("IS_DEPLOY_SITE", "false").lower() == "true":
            print("📌 モックモード: 有効")
            # 環境変数の状態を確認して表示
            has_profile = bool(os.getenv("USER_PROFILE_B64"))
            has_list = bool(os.getenv("VIDEO_LIST_B64"))
            has_details = bool(os.getenv("VIDEO_DETAILS_B64"))

            env_count = sum([has_profile, has_list, has_details])
            if env_count > 0:
                print(f"   ✅ 環境変数: {env_count}/3 設定済み")
                print("   📝 最初のリクエスト時にモックデータをセットアップします")
            else:
                print("   ⚠️ 環境変数が設定されていません")
                print("   📝 ローカル開発環境では正常です（Vercelでは環境変数を設定してください）")
                print("   📝 フォールバックデータが使用されます")
        else:
            print("📌 通常モード: 実際のTikTok APIを使用します")

    app.run(debug=True, port=port, host='0.0.0.0')
