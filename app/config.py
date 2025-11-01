import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

class Config:
    """アプリケーション設定クラス"""

    # TikTok API設定
    TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
    TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
    STATE = "tokentest"

    # デプロイサイト設定
    IS_DEPLOY_SITE = os.getenv("IS_DEPLOY_SITE", "false").lower() == "true"

    # TikTok API設定
    TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize"
    TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

    # セッション設定
    PERMANENT_SESSION_LIFETIME = 24 * 60 * 60  # 24時間（秒）

    # 動画取得設定
    MAX_VIDEO_COUNT = 20  # 一度に取得する動画の最大数

    # ファイルアップロード設定
    MAX_VIDEO_FILE_SIZE = int(os.getenv("MAX_VIDEO_FILE_SIZE", "100")) * 1024 * 1024  # 100MB
    SUPPORTED_VIDEO_TYPES = ["video/mp4", "video/avi", "video/mov", "video/wmv"]
