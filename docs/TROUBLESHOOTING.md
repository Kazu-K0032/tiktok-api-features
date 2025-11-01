# モックデータ表示されない問題のトラブルシューティング

## 原因特定の手順

### ステップ 1: デバッグエンドポイントにアクセス

デプロイ先の URL に以下のパスを追加してアクセス：

```
https://your-vercel-url.vercel.app/debug/mock-data
```

このエンドポイントは以下の情報を JSON 形式で返します。

### ステップ 2: 各項目を確認

#### 2.1 環境変数の確認

```json
{
  "IS_DEPLOY_SITE": "true", // ← "true"であることを確認
  "IS_DEPLOY_SITE_bool": true, // ← trueであることを確認
  "env_vars": {
    "USER_PROFILE_B64_exists": true, // ← trueであることを確認
    "USER_PROFILE_B64_length": 12345, // ← 0でないことを確認（通常は数千文字以上）
    "VIDEO_LIST_B64_exists": true, // ← trueであることを確認
    "VIDEO_LIST_B64_length": 12345, // ← 0でないことを確認
    "VIDEO_DETAILS_B64_exists": true, // ← trueであることを確認
    "VIDEO_DETAILS_B64_length": 12345 // ← 0でないことを確認
  }
}
```

**問題が見つかった場合：**

- 環境変数が設定されていない → Vercel ダッシュボードで環境変数を確認・再設定
- 長さが 0 → Base64 文字列が正しくコピーされていない可能性（改行が入っている可能性）

#### 2.2 モックデータセットアップの確認

```json
{
  "mock_data_setup_done": true, // ← trueになっているか確認
  "mock_data_dir_exists": true, // ← trueであることを確認
  "mock_data_files": {
    "user_profile.json": {
      "exists": true,
      "size": 1234 // ← 0でないことを確認
    },
    "video_list.json": {
      "exists": true,
      "size": 5678 // ← 0でないことを確認
    },
    "video_detail_*.json": {
      "exists": true,
      "size": 1234 // ← 各動画の詳細ファイルが存在するか確認
    }
  }
}
```

**問題が見つかった場合：**

- `mock_data_setup_done`が`false` → セットアップスクリプトが実行されていない
- `mock_data_dir_exists`が`false` → ディレクトリが作成されていない
- ファイルが存在しない、またはサイズが 0 → セットアップスクリプトが失敗している可能性

#### 2.3 モックデータの読み込みテスト

```json
{
  "mock_data_test": {
    "profile_loaded": true, // ← trueであることを確認
    "profile_open_id": "mock_user_123", // ← 実際のopen_idが表示されるか確認
    "video_list_loaded": true, // ← trueであることを確認
    "video_count": 10 // ← 0でないことを確認（実際の動画数）
  }
}
```

**問題が見つかった場合：**

- `profile_loaded`が`false` → ファイルは存在するが読み込みに失敗
- `video_count`が 0 → 動画データが正しく読み込まれていない

## よくある原因と解決方法

### 原因 1: 環境変数の設定漏れ

**症状：**

- `env_vars`の各項目が`false`または`length`が 0

**解決方法：**

1. Vercel ダッシュボード → Settings → Environment Variables
2. 以下の環境変数を確認・再設定：
   - `IS_DEPLOY_SITE` = `true`
   - `USER_PROFILE_B64` = （Base64 文字列、改行なし）
   - `VIDEO_LIST_B64` = （Base64 文字列、改行なし）
   - `VIDEO_DETAILS_B64` = （JSON 形式の Base64 文字列、改行なし）
3. 全ての環境（Production, Preview, Development）に設定されているか確認
4. 再デプロイ

### 原因 2: Base64 文字列に改行が含まれている

**症状：**

- 環境変数は設定されているが、デコードに失敗
- Vercel のログに Base64 デコードエラー

**解決方法：**

1. ローカルで`scripts/encode_mock_data.py`を再実行
2. 出力された Base64 文字列をコピー（**改行を入れない**）
3. Vercel の環境変数に貼り付け
4. 再デプロイ

### 原因 3: セットアップスクリプトが実行されていない

**症状：**

- `mock_data_setup_done`が`false`
- `mock_data_dir_exists`が`false`
- ファイルが存在しない

**解決方法：**

1. Vercel のビルドログを確認
2. `setup_mock_data.py`が実行されているか確認
3. エラーがあれば修正
4. `app.py`の`setup_mock_data_if_needed()`が呼ばれているか確認

### 原因 4: ファイルパスの問題

**症状：**

- `mock_data_dir_exists`が`false`
- パスが正しくない

**解決方法：**

1. Vercel のファイルシステム構造を確認
2. `mock_data`ディレクトリが作成されているか確認
3. パーミッションの問題がないか確認

### 原因 5: IS_DEPLOY_SITE が正しく認識されていない

**症状：**

- `IS_DEPLOY_SITE`が`"true"`だが`IS_DEPLOY_SITE_bool`が`false`
- モックモードが有効にならない

**解決方法：**

1. `app/config.py`の`IS_DEPLOY_SITE`の設定を確認
2. 環境変数は文字列`"true"`として設定
3. `vercel.json`の`env`セクションも確認

## Vercel ログの確認方法

1. Vercel ダッシュボード → プロジェクト → Deployments
2. 該当デプロイを選択
3. **Logs**タブを開く
4. 以下のメッセージを確認：
   - `モックデータのセットアップが完了しました`
   - `✅ user_profile.json を保存しました`
   - `✅ video_list.json を保存しました`
   - エラーメッセージがないか確認

## 手動テスト手順

### ローカルでテスト

```bash
# 環境変数を設定
export IS_DEPLOY_SITE=true
export USER_PROFILE_B64="your_base64_string_here"
export VIDEO_LIST_B64="your_base64_string_here"
export VIDEO_DETAILS_B64='{"video_id": "encoded_string"}'

# アプリを起動
python3 main.py

# ブラウザで http://localhost:3456/debug/mock-data にアクセス
```

### デプロイ先でテスト

1. `https://your-vercel-url.vercel.app/debug/mock-data`にアクセス
2. JSON レスポンスを確認
3. 問題があれば、上記の「よくある原因」を参照して解決

## 再デプロイ手順

問題を修正した後：

1. 変更をコミット & プッシュ：

```bash
git add .
git commit -m "Fix mock data setup"
git push origin main
```

2. Vercel で自動再デプロイが開始される
3. デプロイ完了後、`/debug/mock-data`で再確認
4. 問題が解決していれば、`/`にアクセスしてダッシュボードを確認
