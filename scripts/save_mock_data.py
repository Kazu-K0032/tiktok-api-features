"""実際のAPIレスポンスをモックデータとして保存するスクリプト"""

import json
import os
import sys
import time
from pathlib import Path

# プロジェクトルートを取得
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# make_tiktok_api_requestを直接インポート（生のAPIレスポンスを取得するため）
from app.services.utils import make_tiktok_api_request

def save_json(data: dict, filepath: Path):
    """JSONデータをファイルに保存"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 保存完了: {filepath}")

def get_all_videos(access_token: str, max_videos: int = 100):
    """すべての動画を取得（生のAPIレスポンス）"""
    all_videos = []
    fields = "id,title,cover_image_url,create_time"
    url = "https://open.tiktokapis.com/v2/video/list/"

    # TikTok APIのmax_countは最大20件
    batch_size = 20
    cursor = None
    total_fetched = 0

    print(f"\n📥 動画リストを取得中... (最大{max_videos}件)")

    while total_fetched < max_videos:
        # 取得する件数を計算
        remaining = max_videos - total_fetched
        current_batch = min(batch_size, remaining)

        # リクエストパラメータ
        json_data = {"max_count": current_batch}
        if cursor:
            json_data["cursor"] = cursor

        try:
            response = make_tiktok_api_request(
                method="POST",
                url=f"{url}?fields={fields}",
                access_token=access_token,
                json_data=json_data
            )

            # 動画データを取得
            if "data" in response and "videos" in response["data"]:
                videos = response["data"]["videos"]
                all_videos.extend(videos)
                total_fetched += len(videos)

                print(f"   取得済み: {total_fetched}件 / {len(videos)}件を取得")

                # cursorをチェック（次のページがあるか）
                cursor = response.get("data", {}).get("cursor")
                if not cursor or len(videos) == 0:
                    print("   すべての動画を取得しました")
                    break
            else:
                print("   レスポンスに動画データがありません")
                break

            # APIレート制限対策（少し待機）
            time.sleep(0.5)

        except Exception as e:
            print(f"   ⚠️ エラー: {e}")
            break

    return {
        "data": {
            "videos": all_videos,
            "total": len(all_videos)
        }
    }

def get_video_details_batch(access_token: str, video_ids: list):
    """複数の動画の詳細情報を一括取得（生のAPIレスポンス）"""
    fields = "id,title,duration,view_count,like_count,comment_count,share_count,embed_link,cover_image_url,height,width,create_time"
    url = "https://open.tiktokapis.com/v2/video/query/"

    # TikTok APIのバッチサイズ制限（最大20件）
    batch_size = 20
    all_videos = []

    for i in range(0, len(video_ids), batch_size):
        batch_ids = video_ids[i:i+batch_size]
        print(f"   詳細取得中: {i+1}-{min(i+batch_size, len(video_ids))}件目 / 全{len(video_ids)}件")

        try:
            response = make_tiktok_api_request(
                method="POST",
                url=f"{url}?fields={fields}",
                access_token=access_token,
                json_data={"filters": {"video_ids": batch_ids}}
            )

            if "data" in response and "videos" in response["data"]:
                all_videos.extend(response["data"]["videos"])

            # APIレート制限対策
            time.sleep(0.5)

        except Exception as e:
            print(f"   ⚠️ エラー: {e}")
            continue

    return {
        "data": {
            "videos": all_videos
        }
    }

def main():
    """モックデータを保存"""
    # モックデータディレクトリ
    mock_data_dir = project_root / "mock_data"
    mock_data_dir.mkdir(exist_ok=True)

    # アクセストークンとOpen IDを取得
    access_token = input("アクセストークンを入力してください: ").strip()
    if not access_token:
        print("❌ アクセストークンが必要です")
        return

    max_videos_input = input("取得する動画の最大数（デフォルト: 100）: ").strip()
    max_videos = int(max_videos_input) if max_videos_input else 100

    try:
        # 1. ユーザープロフィールを取得（生のAPIレスポンス）
        print("\n📥 ユーザープロフィールを取得中...")
        profile_response = make_tiktok_api_request(
            method="GET",
            url="https://open.tiktokapis.com/v2/user/info/",
            access_token=access_token,
            params={
                "fields": "open_id,display_name,username,avatar_url,bio_description,profile_web_link,profile_deep_link,is_verified,follower_count,following_count,video_count,likes_count"
            }
        )
        save_json(profile_response, mock_data_dir / "user_profile.json")
        print(f"   レスポンス構造: {list(profile_response.keys())}")

        # 2. すべての動画リストを取得（生のAPIレスポンス）
        video_list_response = get_all_videos(access_token, max_videos)
        save_json(video_list_response, mock_data_dir / "video_list.json")
        print(f"   合計 {len(video_list_response['data']['videos'])} 件の動画を取得しました")

        # 3. 各動画の詳細情報を取得
        if video_list_response["data"]["videos"]:
            video_ids = [video.get("id") for video in video_list_response["data"]["videos"] if video.get("id")]

            if video_ids:
                print(f"\n📥 動画詳細情報を取得中... (全{len(video_ids)}件)")
                video_details_response = get_video_details_batch(access_token, video_ids)

                # 各動画の詳細を個別ファイルとして保存
                if "data" in video_details_response and "videos" in video_details_response["data"]:
                    for video in video_details_response["data"]["videos"]:
                        video_id = video.get("id")
                        if video_id:
                            video_detail_file = {
                                "data": {
                                    "videos": [video]
                                }
                            }
                            save_json(
                                video_detail_file,
                                mock_data_dir / f"video_detail_{video_id}.json"
                            )

                    print(f"   ✅ {len(video_details_response['data']['videos'])} 件の動画詳細を保存しました")

        print("\n✨ モックデータの保存が完了しました！")
        print(f"   保存先: {mock_data_dir}")
        print(f"   - user_profile.json: ユーザープロフィール")
        print(f"   - video_list.json: 動画リスト（{len(video_list_response['data']['videos'])}件）")
        print(f"   - video_detail_*.json: 各動画の詳細情報")

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
