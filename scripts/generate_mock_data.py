"""TikTok APIに依存せずにモックデータ一式を生成するスクリプト

オフラインで以下を生成する:
- static/images/mock/avatars/<open_id>.svg ... アバター画像（リポジトリ同梱）
- static/images/mock/covers/<video_id>.svg ... カバー画像（リポジトリ同梱）
- mock_data/user_profile.json
- mock_data/video_list.json
- mock_data/video_detail_<video_id>.json

JSONの avatar_url / cover_image_url はローカル静的配信パスを指すため、
TikTok CDNの署名付きURLが期限切れになる問題を回避できる。
"""

import json
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
mock_data_dir = project_root / "mock_data"
static_mock_dir = project_root / "static" / "images" / "mock"
avatar_dir = static_mock_dir / "avatars"
cover_dir = static_mock_dir / "covers"


# モックユーザー
USER = {
    "open_id": "mock_open_id_demo_user",
    "display_name": "Demo User",
    "username": "demo_user",
    "bio_description": "Sandbox/モック表示用のデモアカウントです。",
    "profile_web_link": "https://www.tiktok.com/@demo_user",
    "profile_deep_link": "snssdk1234://user/profile?user_id=demo_user",
    "is_verified": False,
    "follower_count": 12_345,
    "following_count": 321,
    "likes_count": 98_765,
    "avatar_initial": "D",
    "avatar_color": "#ff0050",
}

# モック動画（color はカバー背景、emoji は表示文字の代わり）
VIDEOS = [
    {"id": "7300000000000000001", "title": "ダンスチャレンジ #1",     "duration": 15, "color": "#ff0050", "label": "DANCE",  "view_count":  82_310, "like_count": 6_421, "comment_count": 312, "share_count":  98},
    {"id": "7300000000000000002", "title": "簡単レシピ - 5分パスタ",   "duration": 32, "color": "#00f2ea", "label": "COOK",   "view_count": 154_902, "like_count": 9_877, "comment_count": 540, "share_count": 233},
    {"id": "7300000000000000003", "title": "旅行Vlog - 京都の桜",     "duration": 58, "color": "#ffb400", "label": "TRAVEL", "view_count":  47_220, "like_count": 3_104, "comment_count": 188, "share_count":  61},
    {"id": "7300000000000000004", "title": "猫がかわいすぎる件",       "duration": 12, "color": "#7e57c2", "label": "CAT",    "view_count": 312_445, "like_count": 28_991,"comment_count": 1_402,"share_count": 902},
    {"id": "7300000000000000005", "title": "コーディング作業BGM",      "duration": 47, "color": "#26a69a", "label": "CODE",   "view_count":  18_700, "like_count": 1_220, "comment_count":  74, "share_count":  19},
    {"id": "7300000000000000006", "title": "新発売スイーツ食べ比べ",   "duration": 24, "color": "#ec407a", "label": "SWEETS", "view_count":  91_810, "like_count": 7_330, "comment_count": 421, "share_count": 145},
    {"id": "7300000000000000007", "title": "DIY - 棚を作ってみた",     "duration": 63, "color": "#5c6bc0", "label": "DIY",    "view_count":  22_440, "like_count": 1_510, "comment_count":  88, "share_count":  27},
    {"id": "7300000000000000008", "title": "朝のストレッチルーチン",   "duration": 41, "color": "#66bb6a", "label": "FIT",    "view_count":  64_900, "like_count": 4_220, "comment_count": 201, "share_count":  71},
]


def save_json(data: dict, filepath: Path):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON: {filepath.relative_to(project_root)}")


def write_avatar_svg(path: Path, initial: str, color: str):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <circle cx="100" cy="100" r="100" fill="{color}"/>
  <text x="100" y="128" font-family="Helvetica, Arial, sans-serif" font-size="110" font-weight="700" fill="#fff" text-anchor="middle">{initial}</text>
</svg>
'''
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding='utf-8')
    print(f"🖼️  AVATAR: {path.relative_to(project_root)}")


def write_cover_svg(path: Path, label: str, color: str, title: str):
    # タイトルが長すぎる場合は省略
    short_title = title if len(title) <= 16 else title[:15] + "…"
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360" preserveAspectRatio="xMidYMid slice">
  <rect width="640" height="360" fill="{color}"/>
  <rect width="640" height="360" fill="url(#g)" opacity="0.35"/>
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000" stop-opacity="0.7"/>
    </linearGradient>
  </defs>
  <g font-family="Helvetica, Arial, sans-serif" fill="#fff" text-anchor="middle">
    <text x="320" y="170" font-size="64" font-weight="800" letter-spacing="4">{label}</text>
    <text x="320" y="290" font-size="26" font-weight="500">{short_title}</text>
  </g>
</svg>
'''
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding='utf-8')
    print(f"🖼️  COVER:  {path.relative_to(project_root)}")


def main():
    print("📦 オフラインモックデータを生成中...\n")

    # 1. アバター画像
    avatar_filename = f"{USER['open_id']}.svg"
    avatar_path = avatar_dir / avatar_filename
    write_avatar_svg(avatar_path, USER["avatar_initial"], USER["avatar_color"])
    avatar_url = f"/static/images/mock/avatars/{avatar_filename}"

    # 2. user_profile.json
    profile = {
        "data": {
            "user": {
                "open_id": USER["open_id"],
                "display_name": USER["display_name"],
                "username": USER["username"],
                "avatar_url": avatar_url,
                "bio_description": USER["bio_description"],
                "profile_web_link": USER["profile_web_link"],
                "profile_deep_link": USER["profile_deep_link"],
                "is_verified": USER["is_verified"],
                "follower_count": USER["follower_count"],
                "following_count": USER["following_count"],
                "video_count": len(VIDEOS),
                "likes_count": USER["likes_count"],
            }
        }
    }
    save_json(profile, mock_data_dir / "user_profile.json")

    # 3. カバー画像 + video_list.json + video_detail_*.json
    now = int(time.time())
    list_videos = []
    for index, v in enumerate(VIDEOS):
        cover_filename = f"{v['id']}.svg"
        cover_path = cover_dir / cover_filename
        write_cover_svg(cover_path, v["label"], v["color"], v["title"])
        cover_url = f"/static/images/mock/covers/{cover_filename}"
        create_time = now - (index + 1) * 86_400  # 1日ずつ過去にずらす

        list_videos.append({
            "id": v["id"],
            "title": v["title"],
            "cover_image_url": cover_url,
            "create_time": create_time,
        })

        detail = {
            "data": {
                "videos": [{
                    "id": v["id"],
                    "title": v["title"],
                    "duration": v["duration"],
                    "view_count": v["view_count"],
                    "like_count": v["like_count"],
                    "comment_count": v["comment_count"],
                    "share_count": v["share_count"],
                    "embed_link": f"https://www.tiktok.com/embed/{v['id']}",
                    "cover_image_url": cover_url,
                    "create_time": create_time,
                    "height": 1920,
                    "width": 1080,
                }]
            }
        }
        save_json(detail, mock_data_dir / f"video_detail_{v['id']}.json")

    save_json({"data": {"videos": list_videos, "total": len(list_videos)}}, mock_data_dir / "video_list.json")

    print(f"\n✨ 完了: ユーザー1名 / 動画 {len(VIDEOS)} 件")
    print(f"   JSON:   {mock_data_dir.relative_to(project_root)}/")
    print(f"   画像:   {static_mock_dir.relative_to(project_root)}/")
    print("\n💡 次のステップ:")
    print("   - 画像をコミット: git add static/images/mock && git commit")
    print("   - Vercel用Base64を生成: python3 scripts/encode_mock_data.py")


if __name__ == "__main__":
    main()
