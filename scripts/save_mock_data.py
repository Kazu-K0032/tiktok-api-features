"""実APIから取得したモックデータを保存するCLIラッパー

実体は app.services.mock_data_snapshot.snapshot_mock_data
"""

import argparse
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.mock_data_snapshot import snapshot_mock_data


def main():
    parser = argparse.ArgumentParser(description="実APIから取得したモックデータを保存（画像はローカル化）")
    parser.add_argument("--token", help="TikTokアクセストークン (env TIKTOK_ACCESS_TOKEN でも可)")
    parser.add_argument("--max-videos", type=int, default=None, help="取得する動画の最大数 (デフォルト: 100)")
    args = parser.parse_args()

    access_token = (args.token or os.getenv("TIKTOK_ACCESS_TOKEN") or "").strip()
    if not access_token:
        if sys.stdin.isatty():
            access_token = input("アクセストークンを入力してください: ").strip()
        else:
            print("❌ --token または環境変数 TIKTOK_ACCESS_TOKEN を指定してください", file=sys.stderr)
            sys.exit(1)

    max_videos = args.max_videos
    if max_videos is None:
        if sys.stdin.isatty():
            raw = input("取得する動画の最大数（デフォルト: 100）: ").strip()
            max_videos = int(raw) if raw else 100
        else:
            max_videos = 100

    summary = snapshot_mock_data(access_token, max_videos=max_videos, project_root=project_root)

    print("\n--- summary ---")
    print(f"profile_saved        : {summary.get('profile_saved')}")
    print(f"videos_in_list       : {summary.get('videos_in_list')}")
    print(f"video_details_saved  : {summary.get('video_details_saved')}")
    print(f"images_downloaded    : {summary.get('images_downloaded')}")
    if summary.get("errors"):
        print("errors:")
        for e in summary["errors"]:
            print(f"  - {e}")

    print(f"\nJSON: {summary.get('mock_data_dir')}")
    print(f"画像: {summary.get('static_mock_dir')}")
    print("\n💡 次のステップ:")
    print("   - git add static/images/mock && git commit")
    print("   - python3 scripts/encode_mock_data.py  (Vercel用Base64再生成)")


if __name__ == "__main__":
    main()
