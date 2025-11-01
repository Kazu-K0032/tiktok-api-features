"""アプリケーション共通ユーティリティ"""

import logging
import requests
from typing import Dict, Any, List, Optional
from app.config import Config
from app.services.mock_data import get_mock_response

logger = logging.getLogger(__name__)

def make_tiktok_api_request(method: str, url: str, access_token: str,
                           params: Optional[Dict[str, Any]] = None,
                           json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """TikTok APIリクエストを実行"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, params=params, json=json_data, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"TikTok API リクエストエラー: {e}")
        raise

def extract_user_data(response: Dict[str, Any]) -> Dict[str, Any]:
    """APIレスポンスからユーザーデータを抽出"""
    if "data" in response and "user" in response["data"]:
        return response["data"]["user"]
    elif "data" in response:
        return response["data"]
    else:
        return response

def extract_videos_data(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """APIレスポンスから動画データを抽出"""
    if "data" in response and "videos" in response["data"]:
        return response["data"]["videos"]
    elif "data" in response:
        return response["data"]
    else:
        return []

def get_best_image_url(video: Dict[str, Any]) -> Optional[str]:
    """動画から最適な画像URLを取得"""
    # 優先順位: cover_image_url > その他の画像URL
    if video.get("cover_image_url"):
        return video["cover_image_url"]

    # 他の画像フィールドをチェック
    for key in ["image_url", "thumbnail_url", "preview_url"]:
        if video.get(key):
            return video[key]

    return None

def calculate_engagement_rate(like_count: int, comment_count: int, share_count: int, follower_count: int) -> float:
    """平均エンゲージメント率を計算

    Args:
        like_count: いいね数
        comment_count: コメント数
        share_count: シェア数
        follower_count: フォロワー数

    Returns:
        エンゲージメント率（%）、少数第一位で四捨五入
    """
    if follower_count <= 0:
        return 0.0

    # エンゲージメント数を計算
    total_engagement = like_count + comment_count + share_count

    # 基本的なエンゲージメント率を計算
    base_engagement_rate = total_engagement / follower_count * 100

    # フォロワー数に基づく現実的な調整
    # フォロワー数が多いほど、エンゲージメント率は下がる傾向
    if follower_count <= 1000:
        # 小規模アカウント（1000人以下）：調整なし
        engagement_rate = base_engagement_rate
    elif follower_count <= 10000:
        # 中規模アカウント（1000-10000人）：軽微な調整
        engagement_rate = base_engagement_rate * 0.5
    elif follower_count <= 100000:
        # 大規模アカウント（10000-100000人）：中程度の調整
        engagement_rate = base_engagement_rate * 0.3
    else:
        # 超大規模アカウント（100000人以上）：大幅な調整
        engagement_rate = base_engagement_rate * 0.1

    # 現実的な上限を設定（10%を超えないように）
    # TikTokの一般的なエンゲージメント率は1-10%程度
    engagement_rate = min(engagement_rate, 10.0)

    # 少数第一位で四捨五入
    return round(engagement_rate, 1)

def format_engagement_rate(engagement_rate: float) -> str:
    """エンゲージメント率を表示用にフォーマット"""
    if engagement_rate == 0:
        return "0.0%"
    return f"{engagement_rate}%"

def add_engagement_data_to_video(video: Dict[str, Any], follower_count: int) -> Dict[str, Any]:
    """動画データにエンゲージメント情報を追加"""
    like_count = video.get("like_count", 0) or 0
    comment_count = video.get("comment_count", 0) or 0
    share_count = video.get("share_count", 0) or 0

    # エンゲージメント率を計算
    engagement_rate = calculate_engagement_rate(like_count, comment_count, share_count, follower_count)

    # 動画データに追加
    video["engagement_rate"] = engagement_rate
    video["engagement_rate_formatted"] = format_engagement_rate(engagement_rate)

    return video

def calculate_average_engagement_rate(videos: List[Dict[str, Any]], follower_count: int) -> float:
    """
    全動画の合計エンゲージメント率（0～10%）を計算
    videos: 動画のリスト
    follower_count: フォロワー数
    """
    if not videos or follower_count <= 0:
        return 0.0
    total_likes = sum(v.get('like_count', 0) or 0 for v in videos)
    total_comments = sum(v.get('comment_count', 0) or 0 for v in videos)
    total_shares = sum(v.get('share_count', 0) or 0 for v in videos)
    total_engagement = total_likes + total_comments + total_shares
    base_engagement_rate = total_engagement / follower_count * 100
    # calculate_engagement_rateと同じ現実的な調整
    if follower_count <= 1000:
        engagement_rate = base_engagement_rate
    elif follower_count <= 10000:
        engagement_rate = base_engagement_rate * 0.5
    elif follower_count <= 100000:
        engagement_rate = base_engagement_rate * 0.3
    else:
        engagement_rate = base_engagement_rate * 0.1
    engagement_rate = min(engagement_rate, 10.0)
    return round(engagement_rate, 1)

def make_tiktok_api_request(method: str, url: str, access_token: str,
                           params: Optional[Dict[str, Any]] = None,
                           json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """TikTok APIリクエストを実行"""

    # モックモードのチェック
    if Config.IS_DEPLOY_SITE:
        logger.info(f"モックモード: {method} {url}")
        return get_mock_response(url, method, params, json_data)

    # 通常のAPIリクエスト
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, params=params, json=json_data, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"TikTok API リクエストエラー: {e}")
        raise
