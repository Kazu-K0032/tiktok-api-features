"""モックデータ採取の共通ロジック (CLI と Web エンドポイントから共用)

実 TikTok API を叩いて以下を行う:
- ユーザープロフィール / 動画リスト / 動画詳細 を取得
- avatar_url / cover_image_url の画像をダウンロードして
  static/images/mock/{avatars,covers}/ に保存
- JSON 内の URL をローカル静的配信パスに書き換えて mock_data/ に保存

CDN の署名付き URL は期限切れになるため、リポジトリ内に画像を同梱して永続化する。
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from app.services.utils import make_tiktok_api_request

_DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _detect_extension(url: str, content_type: str) -> str:
    path = urlparse(url).path.lower()
    for ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        if path.endswith(ext):
            return '.jpg' if ext == '.jpeg' else ext
    ct = (content_type or '').lower()
    if 'jpeg' in ct or 'jpg' in ct:
        return '.jpg'
    if 'png' in ct:
        return '.png'
    if 'webp' in ct:
        return '.webp'
    if 'gif' in ct:
        return '.gif'
    return '.jpg'


def _existing_local_url(dest_dir: Path, basename: str, project_root: Path) -> Optional[str]:
    if not dest_dir.exists():
        return None
    for p in dest_dir.glob(f"{basename}.*"):
        rel = p.relative_to(project_root)
        return '/' + rel.as_posix()
    return None


def _localize_image(url: Optional[str], dest_dir: Path, basename: str, project_root: Path, log) -> Optional[str]:
    """画像をDLして static/images/mock/... のローカルパスに書き換える。

    - URLが空 / 既にローカルなら何もしない
    - 同名ファイルが既存なら再DLしない
    - 失敗時は元URLを返す（破壊的にならない）
    """
    if not url:
        return url
    if url.startswith('/static/') or url.startswith('static/'):
        return url

    existing = _existing_local_url(dest_dir, basename, project_root)
    if existing:
        return existing

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        ext = _detect_extension(url, resp.headers.get('Content-Type', ''))
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{basename}{ext}"
        dest_path.write_bytes(resp.content)
        rel = dest_path.relative_to(project_root)
        local_url = '/' + rel.as_posix()
        log(f"image saved: {basename} -> {local_url} ({len(resp.content) // 1024} KB)")
        return local_url
    except Exception as e:
        log(f"image download failed ({basename}): {e}")
        return url


def _save_json(data: dict, filepath: Path, log) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"json saved: {filepath.name}")


def _fetch_all_videos(access_token: str, max_videos: int, log) -> Dict[str, Any]:
    fields = "id,title,cover_image_url,create_time"
    url = "https://open.tiktokapis.com/v2/video/list/"
    batch_size = 20
    cursor = None
    total_fetched = 0
    all_videos: List[Dict[str, Any]] = []

    while total_fetched < max_videos:
        remaining = max_videos - total_fetched
        current_batch = min(batch_size, remaining)
        json_data: Dict[str, Any] = {"max_count": current_batch}
        if cursor:
            json_data["cursor"] = cursor

        try:
            response = make_tiktok_api_request(
                method="POST",
                url=f"{url}?fields={fields}",
                access_token=access_token,
                json_data=json_data,
            )
        except Exception as e:
            log(f"video list error: {e}")
            break

        videos = response.get("data", {}).get("videos", [])
        if not videos:
            break
        all_videos.extend(videos)
        total_fetched += len(videos)
        log(f"video list batch: total={total_fetched}")
        cursor = response.get("data", {}).get("cursor")
        if not cursor:
            break
        time.sleep(0.5)

    return {"data": {"videos": all_videos, "total": len(all_videos)}}


def _fetch_video_details(access_token: str, video_ids: List[str], log) -> Dict[str, Any]:
    fields = "id,title,duration,view_count,like_count,comment_count,share_count,embed_link,cover_image_url,height,width,create_time"
    url = "https://open.tiktokapis.com/v2/video/query/"
    batch_size = 20
    all_videos: List[Dict[str, Any]] = []

    for i in range(0, len(video_ids), batch_size):
        batch_ids = video_ids[i:i + batch_size]
        try:
            response = make_tiktok_api_request(
                method="POST",
                url=f"{url}?fields={fields}",
                access_token=access_token,
                json_data={"filters": {"video_ids": batch_ids}},
            )
            all_videos.extend(response.get("data", {}).get("videos", []))
            log(f"video detail batch: {min(i + batch_size, len(video_ids))}/{len(video_ids)}")
        except Exception as e:
            log(f"video detail error: {e}")
            continue
        time.sleep(0.5)

    return {"data": {"videos": all_videos}}


def snapshot_mock_data(
    access_token: str,
    max_videos: int = 100,
    project_root: Optional[Path] = None,
    log=print,
) -> Dict[str, Any]:
    """実APIからモックデータ一式を採取して保存する。

    Returns:
        実行サマリ (件数とエラー情報)
    """
    if not access_token:
        return {"ok": False, "error": "access_token is required"}

    root = project_root or _DEFAULT_PROJECT_ROOT
    mock_data_dir = root / "mock_data"
    static_mock_dir = root / "static" / "images" / "mock"
    avatar_dir = static_mock_dir / "avatars"
    cover_dir = static_mock_dir / "covers"
    mock_data_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "ok": True,
        "profile_saved": False,
        "videos_in_list": 0,
        "video_details_saved": 0,
        "images_downloaded": 0,
        "errors": [],
    }

    image_count_before = (
        len(list(avatar_dir.glob('*'))) if avatar_dir.exists() else 0
    ) + (
        len(list(cover_dir.glob('*'))) if cover_dir.exists() else 0
    )

    # 1) プロフィール
    try:
        profile_response = make_tiktok_api_request(
            method="GET",
            url="https://open.tiktokapis.com/v2/user/info/",
            access_token=access_token,
            params={
                "fields": "open_id,display_name,username,avatar_url,bio_description,profile_web_link,profile_deep_link,is_verified,follower_count,following_count,video_count,likes_count"
            },
        )
        user_obj = profile_response.get("data", {}).get("user", {}) if isinstance(profile_response, dict) else {}
        avatar_url = user_obj.get("avatar_url")
        if avatar_url:
            basename = user_obj.get("open_id") or "default"
            user_obj["avatar_url"] = _localize_image(avatar_url, avatar_dir, basename, root, log)
        _save_json(profile_response, mock_data_dir / "user_profile.json", log)
        summary["profile_saved"] = True
    except Exception as e:
        log(f"profile fetch error: {e}")
        summary["errors"].append(f"profile: {e}")

    # 2) 動画リスト
    try:
        video_list_response = _fetch_all_videos(access_token, max_videos, log)
        for v in video_list_response.get("data", {}).get("videos", []):
            vid = v.get("id")
            cover = v.get("cover_image_url")
            if vid and cover:
                v["cover_image_url"] = _localize_image(cover, cover_dir, vid, root, log)
        _save_json(video_list_response, mock_data_dir / "video_list.json", log)
        videos = video_list_response.get("data", {}).get("videos", [])
        summary["videos_in_list"] = len(videos)
    except Exception as e:
        log(f"video list error: {e}")
        summary["errors"].append(f"video_list: {e}")
        videos = []

    # 3) 動画詳細
    if videos:
        try:
            video_ids = [v.get("id") for v in videos if v.get("id")]
            details = _fetch_video_details(access_token, video_ids, log)
            for v in details.get("data", {}).get("videos", []):
                vid = v.get("id")
                if not vid:
                    continue
                cover = v.get("cover_image_url")
                if cover:
                    v["cover_image_url"] = _localize_image(cover, cover_dir, vid, root, log)
                _save_json({"data": {"videos": [v]}}, mock_data_dir / f"video_detail_{vid}.json", log)
                summary["video_details_saved"] += 1
        except Exception as e:
            log(f"video detail error: {e}")
            summary["errors"].append(f"video_detail: {e}")

    image_count_after = (
        len(list(avatar_dir.glob('*'))) if avatar_dir.exists() else 0
    ) + (
        len(list(cover_dir.glob('*'))) if cover_dir.exists() else 0
    )
    summary["images_downloaded"] = max(0, image_count_after - image_count_before)
    summary["mock_data_dir"] = str(mock_data_dir)
    summary["static_mock_dir"] = str(static_mock_dir)

    return summary
