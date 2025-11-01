import requests
from flask import render_template, redirect, url_for, session, request, jsonify
from app.auth_service import AuthService
from app.services.get_profile import get_user_profile
from app.services.get_video_list import get_video_list, format_create_time
from app.services.get_video_details import get_video_details

from app.services.user_manager import UserManager
from app.utils import get_logger, validate_token
from app.config import Config
from app.services.utils import calculate_engagement_rate, format_engagement_rate, calculate_average_engagement_rate
from app.services.video_upload import upload_video_complete, get_post_status

class Views:
    """ビューコントローラー"""

    def __init__(self):
        from app.config import Config
        self.config = Config()
        self.auth_service = AuthService()
        self.user_manager = UserManager()
        self.logger = get_logger(__name__)
        self.config = Config()

    def index(self):
        """ホームページ"""
        # 認証済みの場合はダッシュボードにリダイレクト
        if self.auth_service.is_authenticated():
            return redirect(url_for("dashboard"))
        return render_template('index.html')

    def login(self):
        """ログイン処理開始"""
        auth_url = self.auth_service.start_auth()
        return redirect(auth_url)

    def callback(self):
        """認証コールバック処理"""
        code = request.args.get("code")
        state = request.args.get("state")

        # コールバック受信

        if not code or not state:
            self.logger.error("コールバックでコードまたはステートが不足しています")
            return "認証に失敗しました (Missing parameters)", 400

        result, error = self.auth_service.handle_callback(code, state)
        if error:
            self.logger.error(f"認証失敗: {error}")
            return error, 400

        # 認証成功、ダッシュボードにリダイレクト
        return redirect(url_for("dashboard"))

    def dashboard(self):
        """ダッシュボード表示"""
        # ダッシュボードアクセス試行
        self.logger.debug(f"ダッシュボードアクセス - セッション内容: {dict(session)}")

        # セッションを永続化（24時間）
        session.permanent = True
        session.modified = True

        # 認証チェック
        if not self.auth_service.is_authenticated():
            self.logger.warning("認証されていません")
            return redirect(url_for("index"))

        # 古いユーザーデータを更新
        self.user_manager.update_all_legacy_users()

        # 現在のユーザーを取得
        current_user = self.user_manager.get_current_user()
        if not current_user:
            self.logger.warning("現在のユーザーが見つかりません")
            return redirect(url_for("index"))

        token = current_user["access_token"]
        open_id = current_user["open_id"]

                    # ダッシュボード - トークン発見

        # トークンの有効性チェック
        if not validate_token(token):
            self.logger.warning(f"無効なアクセストークン形式: {token[:20] if token else 'None'}...")
            # 無効なユーザーを削除
            self.user_manager.remove_user(open_id)
            return redirect(url_for("index"))

                    # トークン検証成功

        try:
            # プロフィール情報と統計情報を一度に取得
            profile = get_user_profile(token)
            # プロフィールと統計データの取得に成功

            # 統計情報が含まれているかチェック
            stats_fields = ["follower_count", "following_count", "video_count", "likes_count"]
            missing_stats = [field for field in stats_fields if field not in profile or profile[field] is None]
            if missing_stats:
                self.logger.warning(f"不足している統計フィールド: {missing_stats}")
                # 不足している統計情報を0で初期化
                for field in missing_stats:
                    profile[field] = 0

            # 動画リストを取得
            all_videos = get_video_list(token, open_id, max_count=self.config.MAX_VIDEO_COUNT)
            # 動画を取得

            # 総シェア数
            total_share_count = sum(v.get('share_count', 0) or 0 for v in all_videos)
            # 総再生数
            total_view_count = sum(v.get('view_count', 0) or 0 for v in all_videos)
            # 平均エンゲージメント率
            avg_engagement_rate = calculate_average_engagement_rate(all_videos, profile.get('follower_count', 0))

            # 全ユーザー情報を取得
            all_users = self.user_manager.get_users()

            # 各ユーザーのセッション期限情報を追加
            for user in all_users:
                user['session_info'] = self.user_manager.get_session_expiry_info(user)

            return render_template('dashboard.html',
                                 profile=profile,
                                 videos=all_videos,  # 全動画を渡す（フロントエンドでページネーション処理）
                                 users=all_users,
                                 current_user=current_user,
                                 total_share_count=total_share_count,
                                 total_view_count=total_view_count,
                                 avg_engagement_rate=avg_engagement_rate)

        except requests.exceptions.HTTPError as e:
            # 401エラー（認証エラー）の場合は特別に処理
            if e.response.status_code == 401:
                self.logger.warning(f"認証エラー（401）: アクセストークンが無効です - {open_id}")
                # 無効なユーザーを削除して再認証を促す
                self.user_manager.remove_user(open_id)
                return redirect(url_for("index"))
            else:
                self.logger.error(f"API通信エラー（HTTP {e.response.status_code}）: {e}")
                return f"API通信でエラーが発生しました（HTTP {e.response.status_code}）。しばらく時間をおいて再度お試しください。", e.response.status_code
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API通信エラー: {e}")
            return "API通信でエラーが発生しました。しばらく時間をおいて再度お試しください。", 503
        except requests.exceptions.Timeout as e:
            self.logger.error(f"API通信タイムアウト: {e}")
            return "API通信がタイムアウトしました。しばらく時間をおいて再度お試しください。", 504
        except Exception as e:
            self.logger.error(f"予期しないエラー: {str(e)}")
            return "システムエラーが発生しました。しばらく時間をおいて再度お試しください。", 500

    def video_detail(self, video_id):
        """動画詳細表示"""
        # 認証チェック
        if not self.auth_service.is_authenticated():
            self.logger.warning("動画詳細で認証されていません")
            return redirect(url_for("index"))

        # 現在のユーザーを取得
        current_user = self.user_manager.get_current_user()
        if not current_user:
            self.logger.warning("動画詳細で現在のユーザーが見つかりません")
            return redirect(url_for("index"))

        token = current_user["access_token"]

        # トークンの有効性チェック
        if not validate_token(token):
            self.logger.warning("動画詳細で無効なアクセストークン形式")
            self.user_manager.remove_user(current_user["open_id"])
            return redirect(url_for("index"))

        try:
            details = get_video_details(token, video_id)
            # 動画詳細を取得

            # プロフィール情報を取得してフォロワー数を取得
            profile = get_user_profile(token)
            follower_count = profile.get("follower_count", 0)

            # エンゲージメント率を計算
            if details and follower_count > 0:
                engagement_rate = calculate_engagement_rate(
                    details.get("like_count", 0),
                    details.get("comment_count", 0),
                    details.get("share_count", 0),
                    follower_count
                )
                details["engagement_rate"] = engagement_rate
                details["engagement_rate_formatted"] = format_engagement_rate(engagement_rate)
            else:
                details["engagement_rate"] = 0.0
                details["engagement_rate_formatted"] = "0.0%"

            # 投稿日時をフォーマット
            if details.get("create_time"):
                details["formatted_create_time"] = format_create_time(details["create_time"])
            else:
                details["formatted_create_time"] = "不明"

            # 全ユーザー情報を取得
            all_users = self.user_manager.get_users()

            # 各ユーザーのセッション期限情報を追加
            for user in all_users:
                user['session_info'] = self.user_manager.get_session_expiry_info(user)

            return render_template('video_detail.html',
                                 d=details,
                                 users=all_users,
                                 current_user=current_user)

        except requests.exceptions.HTTPError as e:
            # 401エラー（認証エラー）の場合は特別に処理
            if e.response.status_code == 401:
                self.logger.warning(f"動画詳細で認証エラー（401）: アクセストークンが無効です - video_id {video_id}")
                # 無効なユーザーを削除して再認証を促す
                self.user_manager.remove_user(current_user["open_id"])
                return redirect(url_for("index"))
            else:
                self.logger.error(f"動画詳細API通信エラー（HTTP {e.response.status_code}） video_id {video_id}: {e}")
                return f"動画情報の取得で通信エラーが発生しました（HTTP {e.response.status_code}）。しばらく時間をおいて再度お試しください。", e.response.status_code
        except requests.exceptions.RequestException as e:
            self.logger.error(f"動画詳細API通信エラー video_id {video_id}: {e}")
            return "動画情報の取得で通信エラーが発生しました。しばらく時間をおいて再度お試しください。", 503
        except requests.exceptions.Timeout as e:
            self.logger.error(f"動画詳細API通信タイムアウト video_id {video_id}: {e}")
            return "動画情報の取得でタイムアウトしました。しばらく時間をおいて再度お試しください。", 504
        except Exception as e:
            self.logger.error(f"動画詳細で予期しないエラー video_id {video_id}: {str(e)}")
            return "動画情報の取得でシステムエラーが発生しました。しばらく時間をおいて再度お試しください。", 500

    # API エンドポイント
    def api_switch_user(self):
        """ユーザー切り替えAPI"""
        open_id = request.json.get('open_id')
        if not open_id:
            return jsonify({'error': 'open_id is required'}), 400

        if self.user_manager.set_current_user(open_id):
            return jsonify({'success': True, 'message': 'ユーザーを切り替えました'})
        else:
            return jsonify({'error': 'ユーザーが見つかりません'}), 404

    def api_remove_user(self):
        """ユーザー削除API"""
        open_id = request.json.get('open_id')
        if not open_id:
            return jsonify({'error': 'open_id is required'}), 400

        if self.user_manager.remove_user(open_id):
            return jsonify({'success': True, 'message': 'ユーザーを削除しました'})
        else:
            return jsonify({'error': 'ユーザーが見つかりません'}), 404

    def api_get_user_data(self):
        """ユーザーデータ取得API（SPA用）"""
        open_id = request.args.get('open_id')
        if not open_id:
            return jsonify({'error': 'open_id is required'}), 400

        user = self.user_manager.get_user_by_open_id(open_id)
        if not user:
            return jsonify({'error': 'ユーザーが見つかりません'}), 404

        try:
            # プロフィール情報を取得
            profile = get_user_profile(user['access_token'])

            # 動画リストを取得
            videos = get_video_list(user['access_token'], open_id, max_count=self.config.MAX_VIDEO_COUNT)

            # 統計情報を計算
            total_share_count = sum(v.get('share_count', 0) or 0 for v in videos)
            total_view_count = sum(v.get('view_count', 0) or 0 for v in videos)
            avg_engagement_rate = calculate_average_engagement_rate(videos, profile.get('follower_count', 0))

            return jsonify({
                'success': True,
                'profile': profile,
                'videos': videos,
                'user_info': {
                    'open_id': user['open_id'],
                    'display_name': user['display_name'],
                    'avatar_url': user['avatar_url'],
                    'total_share_count': total_share_count,
                    'total_view_count': total_view_count,
                    'avg_engagement_rate': avg_engagement_rate
                }
            })

        except Exception as e:
            self.logger.error(f"ユーザーデータ取得エラー: {e}")
            return jsonify({'error': 'データの取得に失敗しました'}), 500

    def api_get_users(self):
        """ユーザーリスト取得API"""
        # 古いユーザーデータを更新
        self.user_manager.update_all_legacy_users()

        users = self.user_manager.get_users()

        # 各ユーザーのセッション期限情報を追加
        for user in users:
            user['session_info'] = self.user_manager.get_session_expiry_info(user)

        return jsonify({
            'success': True,
            'users': users,
            'current_user_open_id': session.get('current_user_open_id')
        })

    def debug_session(self):
        """デバッグ用セッション情報表示"""
        if not self.auth_service.is_authenticated():
            return jsonify({'error': '認証されていません'}), 401

        from flask import current_app

        # セッション設定情報を取得
        session_config = {
            'PERMANENT_SESSION_LIFETIME': current_app.config.get('PERMANENT_SESSION_LIFETIME'),
            'SESSION_TYPE': current_app.config.get('SESSION_TYPE'),
            'SESSION_PERMANENT': current_app.config.get('SESSION_PERMANENT'),
            'SESSION_COOKIE_MAX_AGE': current_app.config.get('SESSION_COOKIE_MAX_AGE'),
            'SESSION_COOKIE_AGE': current_app.config.get('SESSION_COOKIE_AGE'),
            'SESSION_FILE_AGE': current_app.config.get('SESSION_FILE_AGE'),
        }

        # 古いユーザーデータを更新
        self.user_manager.update_all_legacy_users()

        users = self.user_manager.get_users()
        debug_info = []

        for user in users:
            session_info = self.user_manager.get_session_expiry_info(user)
            debug_info.append({
                'open_id': user.get('open_id'),
                'display_name': user.get('display_name'),
                'has_session_expires_at': 'session_expires_at' in user,
                'has_added_at': 'added_at' in user,
                'session_expires_at': user.get('session_expires_at'),
                'added_at': user.get('added_at'),
                'session_info': session_info
            })

        return jsonify({
            'success': True,
            'debug_info': debug_info,
            'session_data': dict(session),
            'session_config': session_config
        })

    def video_upload(self):
        """動画アップロードページ表示"""
        # 認証チェック
        if not self.auth_service.is_authenticated():
            self.logger.warning("動画アップロードで認証されていません")
            return redirect(url_for("index"))

        # 現在のユーザーを取得
        current_user = self.user_manager.get_current_user()
        if not current_user:
            self.logger.warning("動画アップロードで現在のユーザーが見つかりません")
            return redirect(url_for("index"))

        token = current_user["access_token"]
        creator_info_response = None

        try:
            # クリエイター情報を取得してアカウントのプライバシー設定をチェック
            from app.services.video_upload import get_creator_info
            creator_info_response = get_creator_info(token)

            # アカウントのプライバシー設定を確認
            if 'data' in creator_info_response:
                # TikTok APIの仕様に従って、dataフィールドが直接クリエイター情報を含む場合がある
                if 'creator_info' in creator_info_response['data']:
                    creator_info = creator_info_response['data']['creator_info']
                elif 'creator_avatar_url' in creator_info_response['data']:
                    # dataフィールドが直接クリエイター情報を含む場合
                    creator_info = creator_info_response['data']
                else:
                    self.logger.warning("クリエイター情報の形式が不正です")
                    creator_info = {}

                # プライベートアカウント判定
                if 'privacy_level_options' in creator_info:
                    privacy_options = creator_info['privacy_level_options']
                    is_private_account = 'PUBLIC_TO_EVERYONE' not in privacy_options and 'FOLLOWER_OF_CREATOR' in privacy_options

                    if not is_private_account:
                        self.logger.warning("⚠️ アップロードページ表示時: アカウントがプライベート設定ではありません")
                        self.logger.warning("TikTokアプリでアカウントをプライベート設定に変更してください")
                else:
                    self.logger.warning("プライバシー設定オプションが取得できませんでした")
            else:
                self.logger.warning("クリエイター情報の形式が不正です")

        except Exception as e:
            self.logger.error(f"アップロードページ表示時: クリエイター情報取得エラー: {e}")
            import traceback
            self.logger.error(f"エラー詳細: {traceback.format_exc()}")
            # エラーが発生してもページは表示する

        # アカウントのプライバシー設定状況をテンプレートに渡す
        account_status = {
            'is_private': False,
            'privacy_options': [],
            'error': None
        }

        try:
            if creator_info_response and 'data' in creator_info_response:
                # TikTok APIの仕様に従って、dataフィールドが直接クリエイター情報を含む場合がある
                if 'creator_info' in creator_info_response['data']:
                    creator_info = creator_info_response['data']['creator_info']
                elif 'creator_avatar_url' in creator_info_response['data']:
                    # dataフィールドが直接クリエイター情報を含む場合
                    creator_info = creator_info_response['data']
                else:
                    creator_info = {}

                if 'privacy_level_options' in creator_info:
                    privacy_options = creator_info['privacy_level_options']
                    account_status['privacy_options'] = privacy_options
                    # 正しいプライベートアカウント判定
                    account_status['is_private'] = 'PUBLIC_TO_EVERYONE' not in privacy_options and 'FOLLOWER_OF_CREATOR' in privacy_options
        except Exception as e:
            self.logger.error(f"アカウント状況設定エラー: {e}")
            account_status['error'] = 'アカウント情報の取得に失敗しました'

        # 全ユーザー情報を取得
        all_users = self.user_manager.get_users()

        # 各ユーザーのセッション期限情報を追加
        for user in all_users:
            user['session_info'] = self.user_manager.get_session_expiry_info(user)

        return render_template('video_upload.html',
                             account_status=account_status,
                             users=all_users,
                             current_user=current_user)

    def api_upload_video(self):
        """動画アップロードAPI（直接投稿）"""
        return self._handle_video_upload(is_draft=False)

    def api_upload_draft(self):
        """動画下書き投稿API（TikTok下書き）"""
        return self._handle_video_upload(is_draft=True)

    def _handle_video_upload(self, is_draft=False):
        """動画アップロード処理（共通）"""
        upload_type = "下書き投稿" if is_draft else "直接投稿"

        # 認証チェック
        if not self.auth_service.is_authenticated():
            self.logger.error(f"{upload_type}: 認証されていません")
            return jsonify({'success': False, 'error': '認証されていません'}), 401

        # 現在のユーザーを取得
        current_user = self.user_manager.get_current_user()
        if not current_user:
            self.logger.error(f"{upload_type}: ユーザーが見つかりません")
            return jsonify({'success': False, 'error': 'ユーザーが見つかりません'}), 404

        token = current_user["access_token"]

        try:
            # ファイルの確認
            if 'video_file' not in request.files:
                self.logger.error(f"{upload_type}: video_fileがリクエストに含まれていません")
                return jsonify({'success': False, 'error': '動画ファイルが選択されていません'}), 400

            video_file = request.files['video_file']
            if video_file.filename == '':
                self.logger.error(f"{upload_type}: 動画ファイル名が空です")
                return jsonify({'success': False, 'error': '動画ファイルが選択されていません'}), 400

            # ファイルサイズの確認
            video_file.seek(0, 2)
            file_size = video_file.tell()
            video_file.seek(0)

            if file_size == 0:
                self.logger.error(f"{upload_type}: 動画ファイルサイズが0です")
                return jsonify({'success': False, 'error': '動画ファイルが空です'}), 400

            # ファイルサイズ制限チェック
            if file_size > self.config.MAX_VIDEO_FILE_SIZE:
                self.logger.error(f"{upload_type}: ファイルサイズが制限を超えています: {file_size} bytes")
                return jsonify({'success': False, 'error': f'ファイルサイズが大きすぎます。{self.config.MAX_VIDEO_FILE_SIZE // (1024*1024)}MB以下にしてください。'}), 400

            # ファイル形式チェック
            if video_file.content_type not in self.config.SUPPORTED_VIDEO_TYPES:
                self.logger.error(f"{upload_type}: サポートされていないファイル形式: {video_file.content_type}")
                return jsonify({'success': False, 'error': 'サポートされていないファイル形式です。MP4、AVI、MOV、WMV形式のみ対応しています。'}), 400

            # フォームデータの取得
            title = request.form.get('title', '').strip()
            if not title:
                self.logger.error(f"{upload_type}: キャプションが入力されていません")
                return jsonify({'success': False, 'error': 'キャプションを入力してください'}), 400

            # 未監査クライアントはSELF_ONLYのみ許可
            privacy_level = 'SELF_ONLY'
            disable_comment = request.form.get('disable_comment') == 'on'
            disable_duet = request.form.get('disable_duet') == 'on'
            disable_stitch = request.form.get('disable_stitch') == 'on'

            # 一時ファイルとして保存
            import tempfile
            import os

            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                    video_file.save(temp_file.name)
                    temp_file_path = temp_file.name

                # 保存されたファイルのサイズを確認
                saved_file_size = os.path.getsize(temp_file_path)

                if saved_file_size == 0:
                    raise Exception("一時ファイルの保存に失敗しました")

            except Exception as e:
                self.logger.error(f"{upload_type}: 一時ファイル保存エラー: {e}")
                return jsonify({'success': False, 'error': 'ファイルの保存に失敗しました'}), 500

            try:
                # 動画アップロード実行
                success, message, publish_id = upload_video_complete(
                    access_token=token,
                    video_file_path=temp_file_path,
                    title=title,
                    privacy_level=privacy_level,
                    disable_comment=disable_comment,
                    disable_duet=disable_duet,
                    disable_stitch=disable_stitch,
                    is_draft=is_draft
                )

                if success:
                    return jsonify({
                        'success': True,
                        'message': message,
                        'publish_id': publish_id
                    })
                else:
                    self.logger.error(f"{upload_type}: アップロード失敗 - {message}")
                    return jsonify({
                        'success': False,
                        'error': message
                    }), 500

            finally:
                # 一時ファイルを削除
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except Exception as e:
            import traceback
            self.logger.error(f"{upload_type}: 動画アップロードエラー: {e}")
            self.logger.error(f"{upload_type}: エラーの詳細: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': f'アップロードエラー: {str(e)}',
                'debug_info': {
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            }), 500

    def logout(self):
        """ログアウト処理"""
        session.clear()
        # ユーザーマネージャーからも削除
        self.user_manager.clear_current_user()
        return redirect(url_for("index"))


