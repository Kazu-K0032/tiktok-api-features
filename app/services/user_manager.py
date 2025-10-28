"""複数ユーザー管理サービス"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from flask import session
from app.config import Config
from app.services.get_profile import get_user_profile

logger = logging.getLogger(__name__)

class UserManager:
    """複数ユーザー管理クラス"""

    def __init__(self):
        self.config = Config()

    def add_user(self, access_token: str, open_id: str) -> bool:
        """新しいユーザーをセッションに追加"""
        try:
            # 既存のユーザーリストを取得
            users = self.get_users()

            # 既に存在するユーザーかチェック
            for user in users:
                if user.get('open_id') == open_id:
                    logger.info(f"ユーザー {open_id} は既に存在します")
                    return True

            # 最大ユーザー数チェック（デフォルト: 5）
            max_users = 5
            if len(users) >= max_users:
                logger.warning(f"最大ユーザー数 {max_users} に達しました")
                return False

            # ユーザープロフィールを取得
            profile = get_user_profile(access_token)

            # 現在時刻を取得
            current_time = datetime.now()

            # 新しいユーザー情報を作成
            new_user = {
                'open_id': open_id,
                'access_token': access_token,
                'display_name': profile.get('display_name', 'Unknown'),
                'username': profile.get('username', ''),
                'avatar_url': profile.get('avatar_url', ''),
                'follower_count': profile.get('follower_count', 0),
                'video_count': profile.get('video_count', 0),
                'added_at': current_time.isoformat(),
                'session_expires_at': (current_time + timedelta(seconds=self.config.PERMANENT_SESSION_LIFETIME)).isoformat()
            }

            # ユーザーリストに追加
            users.append(new_user)
            session['users'] = users
            session.modified = True

            logger.info(f"ユーザー {open_id} を追加しました")
            return True

        except Exception as e:
            logger.error(f"ユーザー追加エラー: {e}")
            return False

    def get_users(self) -> List[Dict[str, Any]]:
        """セッションからユーザーリストを取得"""
        return session.get('users', [])

    def get_user_by_open_id(self, open_id: str) -> Optional[Dict[str, Any]]:
        """指定されたOpen IDのユーザーを取得"""
        users = self.get_users()
        for user in users:
            if user.get('open_id') == open_id:
                return user
        return None

    def set_current_user(self, open_id: str) -> bool:
        """現在のユーザーを設定"""
        user = self.get_user_by_open_id(open_id)
        if user:
            session['current_user_open_id'] = open_id
            session.modified = True
            logger.info(f"現在のユーザーを {open_id} に設定しました")
            return True
        return False

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """現在のユーザーを取得"""
        current_open_id = session.get('current_user_open_id')
        if current_open_id:
            return self.get_user_by_open_id(current_open_id)
        return None

    def remove_user(self, open_id: str) -> bool:
        """ユーザーを削除"""
        users = self.get_users()
        users = [user for user in users if user.get('open_id') != open_id]
        session['users'] = users
        session.modified = True

        # 削除されたユーザーが現在のユーザーだった場合、最初のユーザーを設定
        if session.get('current_user_open_id') == open_id:
            if users:
                session['current_user_open_id'] = users[0]['open_id']
            else:
                session.pop('current_user_open_id', None)

        logger.info(f"ユーザー {open_id} を削除しました")
        return True

    def clear_current_user(self) -> None:
        """現在のユーザーをクリア"""
        session.pop('current_user_open_id', None)
        session.modified = True
        logger.info("現在のユーザーをクリアしました")

    def update_user_profile(self, open_id: str) -> bool:
        """ユーザープロフィールを更新"""
        user = self.get_user_by_open_id(open_id)
        if not user:
            return False

        try:
            # プロフィールを再取得
            profile = get_user_profile(user['access_token'])

            # ユーザー情報を更新
            user.update({
                'display_name': profile.get('display_name', 'Unknown'),
                'username': profile.get('username', ''),
                'avatar_url': profile.get('avatar_url', ''),
                'follower_count': profile.get('follower_count', 0),
                'video_count': profile.get('video_count', 0),
                'updated_at': datetime.now().isoformat()
            })

            # セッションを更新
            users = self.get_users()
            for i, u in enumerate(users):
                if u.get('open_id') == open_id:
                    users[i] = user
                    break

            session['users'] = users
            session.modified = True

            logger.info(f"ユーザー {open_id} のプロフィールを更新しました")
            return True

        except Exception as e:
            logger.error(f"ユーザープロフィール更新エラー: {e}")
            return False

    def get_user_count(self) -> int:
        """登録されているユーザー数を取得"""
        return len(self.get_users())

    def is_user_registered(self, open_id: str) -> bool:
        """ユーザーが登録されているかチェック"""
        return self.get_user_by_open_id(open_id) is not None

    def get_session_expiry_info(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """ユーザーのセッション期限情報を取得"""
        try:
            if 'session_expires_at' in user:
                expires_at = datetime.fromisoformat(user['session_expires_at'])
                current_time = datetime.now()
                time_remaining = expires_at - current_time

                # セッションが期限切れの場合
                if time_remaining.total_seconds() <= 0:
                    return {
                        'expired': True,
                        'message': 'セッション期限切れ',
                        'expires_at': expires_at.strftime('%Y/%m/%d %H:%M:%S')
                    }

                # 残り時間を計算
                hours = int(time_remaining.total_seconds() // 3600)
                minutes = int((time_remaining.total_seconds() % 3600) // 60)
                seconds = int(time_remaining.total_seconds() % 60)

                if hours > 0:
                    time_str = f"{hours}時間{minutes}分"
                elif minutes > 0:
                    time_str = f"{minutes}分{seconds}秒"
                else:
                    time_str = f"{seconds}秒"

                return {
                    'expired': False,
                    'message': f"{time_str}までセッション維持します",
                    'expires_at': expires_at.strftime('%Y/%m/%d %H:%M:%S'),
                    'time_remaining': time_remaining.total_seconds()
                }
            else:
                # 古いユーザーデータの場合、セッション期限を追加
                self._update_legacy_user_session_info(user)

                # 更新後の情報を再取得
                if 'session_expires_at' in user:
                    return self.get_session_expiry_info(user)
                else:
                    return {
                        'expired': False,
                        'message': 'セッション情報を更新中...',
                        'expires_at': '更新中',
                        'time_remaining': 0
                    }

        except Exception as e:
            logger.error(f"セッション期限情報取得エラー: {e}")
            return {
                'expired': False,
                'message': 'セッション情報を取得できません',
                'expires_at': '不明',
                'time_remaining': 0
            }

    def _update_legacy_user_session_info(self, user: Dict[str, Any]) -> None:
        """古いユーザーデータにセッション期限情報を追加"""
        try:
            # 既に更新済みの場合はスキップ
            if 'session_expires_at' in user:
                return

            # added_atからセッション期限を計算
            if 'added_at' in user:
                try:
                    added_at = datetime.fromisoformat(user['added_at'])
                except:
                    # added_atが無効な場合は現在時刻を使用
                    added_at = datetime.now()
            else:
                # added_atもない場合は現在時刻を使用
                added_at = datetime.now()

            # セッション期限を設定（現在時刻から24時間後）
            current_time = datetime.now()
            session_expires_at = current_time + timedelta(seconds=self.config.PERMANENT_SESSION_LIFETIME)

            # ユーザー情報を更新
            user['added_at'] = current_time.isoformat()
            user['session_expires_at'] = session_expires_at.isoformat()

            # セッションを更新
            users = self.get_users()
            for i, u in enumerate(users):
                if u.get('open_id') == user.get('open_id'):
                    users[i] = user
                    break

            session['users'] = users
            session.modified = True

            logger.info(f"古いユーザーデータ {user.get('open_id')} のセッション期限情報を更新しました")

        except Exception as e:
            logger.error(f"古いユーザーデータの更新エラー: {e}")

    def update_all_legacy_users(self) -> None:
        """すべての古いユーザーデータを更新"""
        try:
            users = self.get_users()
            updated = False

            for user in users:
                if 'session_expires_at' not in user:
                    self._update_legacy_user_session_info(user)
                    updated = True

            if updated:
                logger.info("すべての古いユーザーデータを更新しました")

        except Exception as e:
            logger.error(f"古いユーザーデータ一括更新エラー: {e}")
