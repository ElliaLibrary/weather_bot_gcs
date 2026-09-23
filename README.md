# 天気Bot (Weather Bot)

気象庁の24時間降水量CSVを毎日取得し、Cloud Storage へ保管、Cloud SQL(PostgreSQL)へ登録した上で、処理結果をGmailで通知するバッチ処理。
Google Cloud Functions(第2世代) + Cloud Scheduler + Cloud Storage + Cloud Logging 上で動作する。

通知はGmailで通知する
ログはCloud Loggingで取得する

## 構成

```
Cloud Scheduler (毎日1:00 JST)
    -> Cloud Functions (Gen2) [weather-cron-job]
        -> 気象庁CSVをダウンロード
        -> Cloud Storageへ CSV を保存(クラウド実行時のみ)
        -> Cloud SQL (PostgreSQL) へ登録・ストアド関数実行
        -> Gmail API で結果(完了/失敗)をメール通知
        -> ログは Cloud Logging へ出力
```

## ファイル構成

| ファイル | 役割 |
|---|---|
| `main.py` | Cloud Functionsのエントリーポイント(`functions_framework`) |
| `weather_job.py` | 全体の処理フロー、ログ設定 |
| `downloader.py` | 気象庁CSVのダウンロード |
| `file_upload.py` | Cloud Storageへのアップロード |
| `data_insert.py` | Cloud SQLへのデータ登録・ストアド関数実行 |
| `send_gmail.py` | Gmail APIでの結果通知 |
| `column_config.py` | CSVファイルと登録テーブルの項目のマッピング。項目名に日付を埋める |
| `requirements.txt` | 依存パッケージ |
| `.gcloudignore` / `.gitignore` | デプロイ・Git管理からの除外設定 |

## ログ

- クラウド実行時(`K_SERVICE` 環境変数がある場合)は Cloud Logging へ出力する。Logs Explorer で確認できる。
- ローカル実行時はコンソールへ出力する。
- 失敗は `ERROR` レベルで記録する(`severity>=ERROR` で絞り込み・アラート設定が可能)。

## ローカルでの実行

```powershell
py -3 -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
gcloud auth application-default login
python weather_job.py
```

プロジェクト直下に `.env` を作成し、下記の環境変数をすべて設定しておくこと(`.gitignore`で除外済み、リポジトリには含まれない)。

## 環境変数
「GCS_BUCKET_NAME」 以外はすべて必須とする。(未設定だと起動時に `KeyError` になる)。

| 変数名 | 用途 | 備考 |
|---|---|---|
| `SAVE_DIR` | CSVの保存先ディレクトリ | ローカル: 任意のパス／本番: `/tmp/data` |
| `GCS_BUCKET_NAME` | CSV保管用バケット名 | クラウド実行時のみ使用。ローカルでは省略可。ただし本番では必須ップロードはクラウド実行時のみ |
| `INSTANCE_CONNECTION_NAME` | Cloud SQLインスタンス接続名 | 例: `project-id:region:instance-name` |
| `DB_USER` | DBユーザー名 | |
| `DB_PASSWORD` | DBパスワード | **本番はSecret Manager経由** |
| `DB_DATABASE` | DB名 | |
| `GMAIL_CLIENT_ID` | Gmail用OAuthクライアントID | |
| `GMAIL_CLIENT_SECRET` | Gmail用OAuthクライアントシークレット | **本番はSecret Manager経由** |
| `GMAIL_REFRESH_TOKEN` | Gmail用リフレッシュトークン | **本番はSecret Manager経由** |
| `MAIL_ADRESS` | 通知の宛先メールアドレス | **本番はSecret Manager経由**|
| `SENDER_MAIL_ADRESS` | 通知の送信元メールアドレス | **本番はSecret Manager経由**| |

`TABLE_NAME` / `FUNCTION_NAME`(登録先テーブル名・呼び出すストアド関数名)は環境変数ではなく`data_insert.py`内の定数として管理している。

### `.env` の例(値はダミー)

```
SAVE_DIR=./data
GCS_BUCKET_NAME=your-bucket-name
INSTANCE_CONNECTION_NAME=project-id:asia-northeast1:instance-name
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_DATABASE=your-db-name
GMAIL_CLIENT_ID=xxxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REFRESH_TOKEN=your-refresh-token
MAIL_ADRESS=to@example.com
SENDER_MAIL_ADRESS=from@example.com
```

## Secret Manager の準備

機密値(`DB_PASSWORD` / `GMAIL_CLIENT_ID` /`GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` / `MAIL_ADRESS` / `SENDER_MAIL_ADRESS`)は、Secret Managerに登録してデプロイ時に渡す。

```powershell
# シークレットを作成(初回のみ)
gcloud secrets create DB_PASSWORD --replication-policy=automatic
gcloud secrets create GMAIL_CLIENT_SECRET --replication-policy=automatic
gcloud secrets create GMAIL_REFRESH_TOKEN --replication-policy=automatic
gcloud secrets create MAIL_ADRESS --replication-policy=automatic
gcloud secrets create SENDER_MAIL_ADRESS --replication-policy=automatic

# 値を登録
Set-Content -Path .\secret.tmp -Value "<値>" -NoNewline
gcloud secrets versions add "<シークレット名>" --data-file=.\secret.tmp
Remove-Item .\secret.tmp
```
`DB_PASSWORD`、`MAIL_ADRESS`、`SENDER_MAIL_ADRESS`、`GMAIL_REFRESH_TOKEN`、`GMAIL_CLIENT_ID`、`GMAIL_CLIENT_SECRET`、
の値を登録する。一時ファイル(`secret.tmp`)は、登録後に必ず削除すること。

## 必要な権限(デプロイ用サービスアカウント)

| ロール | 用途 |
|---|---|
| `roles/cloudsql.client` | Cloud SQLへの接続 |
| `roles/storage.objectCreator` | Cloud Storageへの書き込み |
| `roles/logging.logWriter` | Cloud Loggingへの書き込み |
| `roles/secretmanager.secretAccessor` | Secret Managerの値の参照 |

## デプロイ

```powershell
gcloud functions deploy weather-cron-job `
  --gen2 `
  --runtime=python311 `
  --region=asia-northeast1 `
  --source=. `
  --entry-point=scheduled_job `
  --trigger-http `
  --no-allow-unauthenticated `
  --memory=512Mi `
  --service-account=<サービスアカウント> `
  --set-env-vars="INSTANCE_CONNECTION_NAME<プロジェクトID>:<リージョン>:<インスタンス名>,DB_USER=<DBユーザー>,DB_DATABASE=<DB名>,SAVE_DIR=/tmp/data,GCS_BUCKET_NAME=<バケット名>" `
  --set-secrets="DB_PASSWORD=DB_PASSWORD:latest,GMAIL_CLIENT_SECRET=GMAIL_CLIENT_SECRET:latest,GMAIL_REFRESH_TOKEN=GMAIL_REFRESH_TOKEN:latest,MAIL_ADRESS=MAIL_ADRESS:latest,GMAIL_CLIENT_ID=GMAIL_CLIENT_ID:latest,SENDER_MAIL_ADRESS=SENDER_MAIL_ADRESS:latest"

```

定期実行はCloud Schedulerから認証つき(OIDC)でこのエンドポイントを呼び出す構成。

## 注意事項
- `--set-env-vars` / `--set-secrets` はデプロイのたびに指定内容で完全に上書きされる。
　一部だけ変更したコマンドを使い回すと、書き忘れた項目が消えるので、常に全項目を含む完全なコマンドを使うこと。
- 環境変数が1つでも足りない場合、関数は起動時にエラーになる(ログにはどの変数が原因の `KeyError` が出る)。
- ローカルの `venv/`、`.env`、`client_secret.json` はデプロイ対象・Git管理のどちらからも除外している(`.gitignore` / `.gcloudignore`)。
- Gmailのリフレッシュトークンが失効すると通知メールが送れなくなる。
　ログに `Gmail送信に失敗しました` が出たら、トークンを再取得して Secret Manager に新しいバージョンを登録する。