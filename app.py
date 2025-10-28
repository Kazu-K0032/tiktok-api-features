import logging
from flask import Flask
# from flask_session import Session  # 標準のFlaskセッションを使用
from app.config import Config
from app.views import Views
from app.utils import setup_logging, cleanup_caches

def create_app():
    """Flaskアプリケーションを作成"""
    # ログ設定を初期化
    setup_logging()

    app = Flask(__name__, static_folder='static', template_folder='templates')

    # 設定を適用
    config = Config()
    app.secret_key = "tiktok_api_secret_key_2024"  # セッション機能に必要

    # ビューコントローラーを初期化
    views = Views()

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

    # 定期的なキャッシュクリーンアップ
    @app.before_request
    def before_request():
        # リクエストの10%でキャッシュクリーンアップを実行
        import random
        if random.random() < 0.1:
            cleanup_caches()

    return app

if __name__ == "__main__":
    # source venv/bin/activate
    # python app.py
    from dotenv import load_dotenv
    from app.utils import get_app_port

    # 環境変数を読み込み
    load_dotenv()

    app = create_app()

    # ポートを取得
    port = get_app_port()

    # サーバー起動前にリンクを出力
    print(f"ローカルアクセス: http://127.0.0.1:{port}")

    app.run(debug=True, port=port, host='0.0.0.0')
