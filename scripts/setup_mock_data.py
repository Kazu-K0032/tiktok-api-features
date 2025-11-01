"""Vercelビルド時にモックデータを環境変数から復号して保存するスクリプト"""

import os
import json
import base64
import sys
from pathlib import Path

def decode_and_save(env_var_name: str, output_path: Path):
    """環境変数からBase64文字列を取得して復号し、ファイルに保存"""
    encoded_data = os.getenv(env_var_name)
    if not encoded_data:
        print(f"⚠️ 環境変数 {env_var_name} が見つかりません", file=sys.stderr)
        return False

    try:
        decoded_data = base64.b64decode(encoded_data).decode('utf-8')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(decoded_data)
        print(f"✅ {output_path} を保存しました", file=sys.stderr)
        return True
    except Exception as e:
        print(f"❌ エラー ({env_var_name}): {e}", file=sys.stderr)
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
        return False

def main():
    """モックデータを環境変数から復号して保存"""
    try:
        mock_data_dir = Path(__file__).parent.parent / "mock_data"
        mock_data_dir.mkdir(parents=True, exist_ok=True)

        print("📥 モックデータを環境変数から復号中...\n", file=sys.stderr)

        success_count = 0

        # user_profile.json
        if decode_and_save("USER_PROFILE_B64", mock_data_dir / "user_profile.json"):
            success_count += 1

        # video_list.json
        if decode_and_save("VIDEO_LIST_B64", mock_data_dir / "video_list.json"):
            success_count += 1

        # 動画詳細ファイル
        video_details_json = os.getenv("VIDEO_DETAILS_B64")
        if video_details_json:
            try:
                video_details = json.loads(video_details_json)
                for video_id, encoded_data in video_details.items():
                    try:
                        decoded_data = base64.b64decode(encoded_data).decode('utf-8')
                        output_path = mock_data_dir / f"video_detail_{video_id}.json"
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(decoded_data)
                        print(f"✅ {output_path} を保存しました", file=sys.stderr)
                        success_count += 1
                    except Exception as e:
                        print(f"❌ 動画詳細 {video_id} の復号エラー: {e}", file=sys.stderr)
                        import traceback
                        print(traceback.format_exc(), file=sys.stderr)
            except Exception as e:
                print(f"❌ 動画詳細の解析エラー: {e}", file=sys.stderr)
                import traceback
                print(traceback.format_exc(), file=sys.stderr)
        else:
            print("⚠️ 環境変数 VIDEO_DETAILS_B64 が見つかりません", file=sys.stderr)

        # ファイルが作成された場合のみ成功メッセージを表示
        if success_count > 0:
            print(f"\n✨ モックデータのセットアップが完了しました！ ({success_count} ファイル)", file=sys.stderr)
        else:
            print(f"\n⚠️ モックデータファイルが作成されませんでした（{success_count} ファイル）", file=sys.stderr)
            print("   環境変数（USER_PROFILE_B64, VIDEO_LIST_B64, VIDEO_DETAILS_B64）が正しく設定されているか確認してください。", file=sys.stderr)
            print("   これは通常、ローカル開発環境では正常な動作です。", file=sys.stderr)

    except Exception as e:
        print(f"❌ 致命的なエラー: {e}", file=sys.stderr)
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
        # エラーが発生してもアプリケーションは起動できるようにする
        # Vercelでは環境変数がない場合でもアプリは動作するようにする
        pass

if __name__ == "__main__":
    main()

