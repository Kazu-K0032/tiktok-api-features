"""モックデータ定義"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# モックデータディレクトリのパス
MOCK_DATA_DIR = Path(__file__).parent.parent.parent / "mock_data"

def load_json_file(filename: str) -> Optional[Dict[str, Any]]:
    """JSONファイルを読み込む"""
    filepath = MOCK_DATA_DIR / filename
    if not filepath.exists():
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ モックデータ読み込みエラー ({filename}): {e}")
        return None

def get_mock_user_profile() -> Dict[str, Any]:
    """モックユーザープロフィールデータ（実際のAPIレスポンスから）"""
    # JSONファイルから読み込みを試行
    data = load_json_file("user_profile.json")
    if data and "data" in data and "user" in data["data"]:
        return data["data"]["user"]

    # フォールバック: ファイルがない場合のデフォルトデータ
    return {
        "open_id": "mock_user_123",
        "display_name": "モックユーザー",
        "username": "mock_user",
        "avatar_url": "https://via.placeholder.com/150",
        "bio_description": "これはモックデータです",
        "profile_web_link": "https://www.tiktok.com/@mock_user",
        "profile_deep_link": "snssdk1234://user/profile?user_id=mock_user",
        "is_verified": False,
        "follower_count": 1000,
        "following_count": 500,
        "video_count": 50,
        "likes_count": 5000
    }

def get_mock_video_list() -> Dict[str, Any]:
    """モック動画リストデータ（実際のAPIレスポンスから）"""
    # JSONファイルから読み込みを試行
    data = load_json_file("video_list.json")
    if data:
        return data

    # フォールバック
    current_time = int(datetime.now().timestamp())
    return {
        "data": {
            "videos": [
                {
                    "id": "mock_video_1",
                    "title": "モック動画 1",
                    "duration": 30,
                    "view_count": 10000,
                    "like_count": 500,
                    "comment_count": 50,
                    "share_count": 20,
                    "embed_link": "https://www.tiktok.com/embed/mock_video_1",
                    "cover_image_url": "https://via.placeholder.com/640x360",
                    "create_time": current_time - 86400,
                    "height": 720,
                    "width": 1280
                },
                {
                    "id": "mock_video_2",
                    "title": "モック動画 2",
                    "duration": 45,
                    "view_count": 5000,
                    "like_count": 300,
                    "comment_count": 30,
                    "share_count": 10,
                    "embed_link": "https://www.tiktok.com/embed/mock_video_2",
                    "cover_image_url": "https://via.placeholder.com/640x360",
                    "create_time": current_time - 172800,
                    "height": 1080,
                    "width": 1920
                }
            ]
        }
    }

def get_mock_video_detail(video_id: str) -> Dict[str, Any]:
    """モック動画詳細データ（実際のAPIレスポンスから）"""
    # まずvideo_id固有のファイルを探す
    specific_file = f"video_detail_{video_id}.json"
    data = load_json_file(specific_file)
    if data:
        return data

    # 汎用的なファイルを探す
    data = load_json_file("video_detail.json")
    if data:
        # video_idを更新
        if "data" in data and "videos" in data["data"] and data["data"]["videos"]:
            data["data"]["videos"][0]["id"] = video_id
        return data

    # フォールバック
    current_time = int(datetime.now().timestamp())
    return {
        "data": {
            "videos": [
                {
                    "id": video_id,
                    "title": f"モック動画 {video_id}",
                    "duration": 30,
                    "view_count": 15000,
                    "like_count": 750,
                    "comment_count": 75,
                    "share_count": 30,
                    "embed_link": f"https://www.tiktok.com/embed/{video_id}",
                    "cover_image_url": "https://via.placeholder.com/640x360",
                    "create_time": current_time - 86400,
                    "height": 720,
                    "width": 1280
                }
            ]
        }
    }

def get_mock_response(url: str, method: str, params: Dict = None, json_data: Dict = None) -> Dict[str, Any]:
    """URLとパラメータに基づいて適切なモックデータを返す"""

    # ユーザープロフィール情報
    if "v2/user/info/" in url:
        return {
            "data": {
                "user": get_mock_user_profile()
            }
        }

    # 動画リスト
    if "v2/video/list/" in url:
        return get_mock_video_list()

    # 動画クエリ（詳細）
    if "v2/video/query/" in url:
        if json_data and "filters" in json_data and "video_ids" in json_data["filters"]:
            video_id = json_data["filters"]["video_ids"][0]
            return get_mock_video_detail(video_id)
        return get_mock_video_list()

    # デフォルト（認証系など）
    return {
        "data": {},
        "error": {
            "code": "MOCK_MODE",
            "message": "モックモードです"
        }
    }
