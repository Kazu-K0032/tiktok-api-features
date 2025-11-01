"""モックデータをBase64エンコードして環境変数用に出力するスクリプト"""

import base64
import json
from pathlib import Path

def encode_file(filepath: Path) -> str:
    """ファイルをBase64エンコード"""
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def main():
    """モックデータをBase64エンコードして出力"""
    mock_data_dir = Path(__file__).parent.parent / "mock_data"
    output = {}

    print("📦 モックデータをBase64エンコード中...\n")

    # user_profile.json
    user_profile_path = mock_data_dir / "user_profile.json"
    if user_profile_path.exists():
        output['USER_PROFILE_B64'] = encode_file(user_profile_path)
        print(f"✅ user_profile.json をエンコードしました ({len(output['USER_PROFILE_B64'])} 文字)")
    else:
        print("⚠️ user_profile.json が見つかりません")

    # video_list.json
    video_list_path = mock_data_dir / "video_list.json"
    if video_list_path.exists():
        output['VIDEO_LIST_B64'] = encode_file(video_list_path)
        print(f"✅ video_list.json をエンコードしました ({len(output['VIDEO_LIST_B64'])} 文字)")
    else:
        print("⚠️ video_list.json が見つかりません")

    # 動画詳細ファイル
    video_detail_files = list(mock_data_dir.glob("video_detail_*.json"))
    if video_detail_files:
        video_details = {}
        for file in sorted(video_detail_files):
            video_id = file.stem.replace("video_detail_", "")
            video_details[video_id] = encode_file(file)
            print(f"✅ {file.name} をエンコードしました")

        # JSON文字列として保存
        output['VIDEO_DETAILS_B64'] = json.dumps(video_details)
        print(f"✅ 動画詳細ファイル {len(video_detail_files)} 件をエンコードしました")
    else:
        print("⚠️ 動画詳細ファイルが見つかりません")

    print("\n" + "="*60)
    print("以下の環境変数をVercelに設定してください：")
    print("="*60 + "\n")

    for key, value in output.items():
        if key == 'VIDEO_DETAILS_B64':
            # JSON形式の場合はそのまま表示
            print(f"{key}=")
            print(json.dumps(json.loads(value), indent=2, ensure_ascii=False))
        else:
            # Base64文字列の場合は改行なしで表示
            print(f"{key}={value}")
        print()

    # ファイルにも保存（オプション）
    output_file = Path(__file__).parent.parent / "mock_data_env_vars.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Vercel環境変数設定用\n")
        f.write("# 以下の値をVercelのEnvironment Variablesにコピー&ペーストしてください\n\n")
        for key, value in output.items():
            if key == 'VIDEO_DETAILS_B64':
                f.write(f"{key}=\n")
                f.write(json.dumps(json.loads(value), indent=2, ensure_ascii=False))
            else:
                f.write(f"{key}={value}\n")
            f.write("\n")

    print(f"✅ 環境変数設定用ファイルを保存しました: {output_file}")
    print("\n💡 注意: Base64エンコードされたデータは非常に長い文字列です。")
    print("   Vercelの環境変数設定画面で、改行なしでコピー&ペーストしてください。")

if __name__ == "__main__":
    main()

