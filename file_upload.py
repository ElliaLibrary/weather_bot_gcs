from google.cloud import storage
from pathlib import Path
import os
import logging
logger = logging.getLogger("file_upload")

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

def upload_to_gcs(file_path: Path,dest_blob_name: str) -> bool:

    if not GCS_BUCKET_NAME:
        logger.error("GCS_BUCKET_NAME が設定されていません")
        return False
    
    if not file_path.exists():
        logger.error(f"アップロード対象のファイルが存在しません: {file_path}")
        return False

    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(dest_blob_name)
        blob.upload_from_filename(str(file_path))
        logger.info(f"GCSへアップロードしました: gs://{GCS_BUCKET_NAME}/{dest_blob_name}")
        return True
    except Exception as e:
        logger.error(f"【エラー】GCSへのアップロードに失敗しました: {e}", exc_info=True)
        return False
    
