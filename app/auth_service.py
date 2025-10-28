import hashlib
import string
import random
import requests
import logging
from flask import request, session
from app.config import Config
from app.services.user_manager import UserManager

logger = logging.getLogger(__name__)

class AuthService:
    """TikTok認証サービス"""

    def __init__(self):
        self.config = Config()
        self.user_manager = UserManager()
        # メモリ内ストレージ（セッションの代替）
        self.session_data = {}

    def generate_pkce(self):
        """PKCE用のcode_verifierとcode_challengeを生成（TikTok公式仕様準拠）"""
        # (1) code_verifier を 43文字以上のunreserved charsで生成
        chars = string.ascii_letters + string.digits + '-._~'
        code_verifier = ''.join(random.choice(chars) for _ in range(64))

        # (2) TikTok方式のchallengeはhex digest
        code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).hexdigest()

        # デバッグ情報
        logger.debug(f"PKCE - 検証子の長さ: {len(code_verifier)}")
        logger.debug(f"PKCE - チャレンジの長さ: {len(code_challenge)}")
        logger.debug(f"PKCE - 検証子: {code_verifier}")
        logger.debug(f"PKCE - チャレンジ: {code_challenge}")
        logger.debug(f"PKCE - チャレンジが16進数: {all(c in '0123456789abcdef' for c in code_challenge)}")

        # 検証用のデバッグ
        logger.debug(f"PKCE - 検証子が予約されていない文字のみ: {all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~' for c in code_verifier)}")

        return code_verifier, code_challenge

    def get_redirect_uri(self):
        """動的にリダイレクトURIを生成（TikTokポータル設定と完全一致させる）"""
        # request.scheme と request.host を使い、常に実際のアクセス先と一致させる
        base_url = f"{request.scheme}://{request.host}"

        # GitHub Pagesの場合の処理
        if "github.io" in request.host:
            # GitHub Pagesの場合は、実際のアクセスURLに基づいてリダイレクトURIを生成
            redirect_uri = f"{base_url}/tiktok-api-features/callback/"
        else:
            # ローカル開発環境の場合
            redirect_uri = f"{base_url}/callback/"

        logger.info(f"ホスト: {request.host}")
        logger.info(f"生成されたリダイレクトURI: {redirect_uri}")
        return redirect_uri

    def start_auth(self):
        """認証プロセスを開始"""
        # 既存のユーザー情報を保持し、PKCE関連のデータのみクリア
        existing_users = session.get('users', [])
        existing_current_user = session.get('current_user_open_id')

        # PKCE関連のデータのみクリア
        session.pop('code_verifier', None)
        self.session_data.clear()  # メモリ保存もクリア

        # 既存のユーザー情報を復元
        if existing_users:
            session['users'] = existing_users
        if existing_current_user:
            session['current_user_open_id'] = existing_current_user

        uri = self.get_redirect_uri()

        # PKCEパラメータを生成
        code_verifier, code_challenge = self.generate_pkce()

        # セッションとメモリ内ストレージの両方に保存
        session.permanent = True
        session['code_verifier'] = code_verifier
        session.modified = True  # セッション変更を強制保存

        # メモリ内ストレージにも保存（メインストレージとして使用）
        self.session_data['code_verifier'] = code_verifier

        # 保存確認のデバッグ
        logger.debug(f"ログイン - セッションcode_verifier: {session.get('code_verifier', 'None')[:10]}...")
        logger.debug(f"ログイン - メモリcode_verifier: {self.session_data.get('code_verifier', 'None')[:10]}...")

        # デバッグ情報を出力
        logger.debug(f"セッションID: {session.sid if hasattr(session, 'sid') else 'N/A'}")
        logger.debug(f"Code Verifier保存済み: {code_verifier[:10]}...")
        logger.debug(f"セッション内容: {dict(session)}")
        logger.debug(f"メモリストレージ: {self.session_data}")

        params = {
            "client_key": self.config.TIKTOK_CLIENT_KEY,
            "scope": "user.info.basic,user.info.profile,user.info.stats,video.list,video.publish,video.upload",
            "response_type": "code",
            "redirect_uri": uri,
            "state": self.config.STATE,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        url = self.config.TIKTOK_AUTH_URL + "?" + "&".join(f"{k}={v}" for k,v in params.items())

        # デバッグ情報を出力
        logger.info(f"クライアントキー: {self.config.TIKTOK_CLIENT_KEY}")
        logger.info(f"リダイレクトURI: {uri}")
        logger.info(f"コードチャレンジ: {code_challenge}")
        logger.info(f"認証URL: {url}")

        return url

    def handle_callback(self, code, state):
        """認証コールバックを処理"""
        # デバッグ情報を出力
        logger.debug(f"コールバック - セッション内容: {dict(session)}")
        logger.debug(f"コールバック - メモリストレージ: {self.session_data}")
        logger.debug(f"コールバック - コード: {code[:20] if code else 'None'}...")
        logger.debug(f"コールバック - ステート: {state}")

        if state != self.config.STATE or not code:
            return None, "認証に失敗しました (Invalid state/code)"

        # メモリ保存されたcode_verifierを優先利用（セッションの不整合を回避）
        code_verifier = self.session_data.get('code_verifier')
        if not code_verifier:
            # フォールバック: セッションから取得
            code_verifier = session.get('code_verifier')

        logger.debug(f"コールバック - Code Verifier: {code_verifier[:10] if code_verifier else 'None'}...")
        logger.debug(f"コールバック - Code Verifierの取得元: {'memory' if self.session_data.get('code_verifier') else 'session'}")

        if not code_verifier:
            logger.error("コールバックでcode_verifierが見つかりません")
            return None, "認証に失敗しました (Missing code_verifier)"

        # Access Token の取得
        token_request_data = {
            "client_key": self.config.TIKTOK_CLIENT_KEY,
            "client_secret": self.config.TIKTOK_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.get_redirect_uri(),
            "code_verifier": code_verifier
        }

        logger.debug(f"トークン要求 - Code Verifier: {code_verifier}")
        logger.debug(f"トークン要求 - リダイレクトURI: {self.get_redirect_uri()}")

        try:
            token_res = requests.post(
                self.config.TIKTOK_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=token_request_data,
                timeout=30
            )

            logger.debug(f"トークンレスポンスステータス: {token_res.status_code}")

            if token_res.status_code != 200:
                logger.error(f"トークンエラー: {token_res.status_code} - {token_res.text}")
                return None, f"Token Error: {token_res.text}"

            # レスポンスの詳細をデバッグ出力
            response_json = token_res.json()
            logger.debug(f"トークンレスポンスJSON: {response_json}")

            # TikTok v2の仕様に合わせて、ルート直下からアクセス
            if "access_token" in response_json:
                access_token = response_json["access_token"]
                open_id = response_json["open_id"]
                logger.info(f"ルートでアクセストークンを発見: {access_token[:20]}...")
            elif "data" in response_json:
                # 互換性のため、dataフィールドもサポート
                data = response_json["data"]
                access_token = data.get("access_token")
                open_id = data.get("open_id")
                logger.info(f"dataフィールドでアクセストークンを発見: {access_token[:20] if access_token else 'None'}...")
            else:
                logger.error(f"レスポンスでアクセストークンが見つかりません: {response_json}")
                return None, f"Access token not found in response: {response_json}"

            if not access_token:
                logger.error(f"レスポンスでアクセストークンが空です: {response_json}")
                return None, f"Access token is empty in response: {response_json}"

            # ユーザーをセッションに追加
            if self.user_manager.add_user(access_token, open_id):
                # 最初のユーザーまたは唯一のユーザーの場合、現在のユーザーに設定
                if self.user_manager.get_user_count() == 1:
                    self.user_manager.set_current_user(open_id)

                # セッションを永続化（24時間）
                session.permanent = True
                session.modified = True

                # code_verifierを削除（セキュリティのため）
                session.pop('code_verifier', None)

                logger.info(f"認証成功、ユーザー追加済み - トークン: {access_token[:20]}..., Open ID: {open_id}")
                logger.debug(f"保存後のセッション: {dict(session)}")
                return {"access_token": access_token, "open_id": open_id}, None
            else:
                logger.error("ユーザーの追加に失敗しました")
                return None, "ユーザーの追加に失敗しました"

        except requests.exceptions.RequestException as e:
            logger.error(f"トークン交換中のリクエスト例外: {e}")
            return None, f"Network error: {str(e)}"
        except Exception as e:
            logger.error(f"トークン交換中の予期しないエラー: {e}")
            return None, f"Unexpected error: {str(e)}"

    def is_authenticated(self):
        """認証済みかどうかをチェック"""
        return self.user_manager.get_user_count() > 0

    def get_current_user_token(self):
        """現在のユーザーのアクセストークンを取得"""
        current_user = self.user_manager.get_current_user()
        if current_user:
            return current_user.get('access_token')
        return None
