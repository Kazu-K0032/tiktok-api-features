# Vercel デプロイ手順

このドキュメントでは、Vercel にデプロイする際にモックデータを使用する手順を説明します。

## 前提条件

- ローカルでモックデータが作成済み（`mock_data/`ディレクトリに JSON ファイルがある）
- Vercel アカウントとプロジェクトが設定済み

## 手順

### ステップ 1: モックデータを Base64 エンコード

```bash
python3 scripts/encode_mock_data.py
```

このスクリプトは以下を実行します：

- `mock_data/user_profile.json`を Base64 エンコード
- `mock_data/video_list.json`を Base64 エンコード
- `mock_data/video_detail_*.json`を Base64 エンコード（全ての動画詳細ファイル）

出力結果が表示され、`mock_data_env_vars.txt`ファイルにも保存されます。

### ステップ 2: Vercel の環境変数を設定

Vercel ダッシュボードで以下を設定：

1. **プロジェクトを選択** → **Settings** → **Environment Variables**

2. 以下の環境変数を追加：

   - **USER_PROFILE_B64**

     - Value: エンコードスクリプトで出力された`USER_PROFILE_B64`の値
     - Environment: Production, Preview, Development（全て）

   - **VIDEO_LIST_B64**

     - Value: エンコードスクリプトで出力された`VIDEO_LIST_B64`の値
     - Environment: Production, Preview, Development（全て）

   - **VIDEO_DETAILS_B64**

     - Value: エンコードスクリプトで出力された`VIDEO_DETAILS_B64`の値（JSON 形式）
     - Environment: Production, Preview, Development（全て）

   - **IS_DEPLOY_SITE**
     - Value: `true`
     - Environment: Production, Preview, Development（全て）

3. その他の必要な環境変数も設定：
   - `TIKTOK_CLIENT_KEY`
   - `TIKTOK_CLIENT_SECRET`
   - `APP_PORT` (オプション、デフォルト: 3456)

**注意**: Base64 エンコードされた文字列は非常に長いです。改行なしでコピー&ペーストしてください。

### ステップ 3: デプロイ

```bash
# Vercel CLIを使用する場合
vercel --prod

# または GitHubと連携している場合、pushすると自動デプロイ
git push origin main
```

### ステップ 4: 動作確認

デプロイ後、アプリケーションにアクセスして以下を確認：

1. ダッシュボードが表示される
2. モックデータが正しく読み込まれている
3. 画像（cover_image_url）が表示される

## 動作の仕組み

1. **アプリケーション起動時**: `main.py`の`create_app()`関数が呼ばれる
2. **モックデータセットアップ**: `IS_DEPLOY_SITE=true`の場合、`setup_mock_data.py`が自動実行される
3. **環境変数から復号**: Base64 エンコードされたデータを復号して`mock_data/`ディレクトリに保存
4. **モックモード有効化**: `IS_DEPLOY_SITE=true`により、API リクエストがモックデータを使用

## トラブルシューティング

### モックデータが読み込まれない

1. 環境変数が正しく設定されているか確認
2. Vercel のログでエラーを確認：
   ```bash
   vercel logs
   ```
3. `IS_DEPLOY_SITE=true`が設定されているか確認
4. 環境変数の値が正しくコピーされているか確認（改行が入っていないか）

### Base64 文字列が長すぎる

Vercel の環境変数には文字数制限があります（通常 250KB 程度）。動画数が多い場合は：

- `VIDEO_DETAILS_B64`に含める動画数を減らす
- または、重要な動画のみを含める

### 環境変数の更新

モックデータを更新した場合：

1. `scripts/encode_mock_data.py`を再実行
2. Vercel の環境変数を更新
3. 再デプロイ

### デプロイ時のエラー

- Python バージョンの確認（Vercel は自動検出しますが、必要に応じて`runtime.txt`を作成）
- 依存関係の確認（`requirements.txt`が正しく設定されているか）

## 注意事項

- **GitHub リポジトリにはモックデータを含めない**: `.gitignore`で除外されています
- **環境変数は機密情報として扱う**: 実際の API レスポンスを含む可能性があります
- **Base64 データは大きい**: 環境変数のサイズ制限に注意してください
- **モックデータの更新**: API レスポンスを更新した場合は、エンコード → 環境変数更新 → 再デプロイが必要です

## ファイル構成

```
tiktok-api-features/
├── scripts/
│   ├── encode_mock_data.py      # モックデータをBase64エンコード
│   └── setup_mock_data.py       # 環境変数からモックデータを復号
├── mock_data/                   # モックデータディレクトリ（Git除外）
├── main.py                      # アプリケーション（自動セットアップ機能付き）
├── vercel.json                  # Vercel設定
└── DEPLOY.md                    # このドキュメント
```
