import requests
import logging
logger = logging.getLogger("Downloader")

def download_jma_csv(url: str,output_filepath: str) -> bool:
    """
    気象庁のCSVデータをダウンロードし、指定パスに保存・ログ出力を行う関数
    """
    try:
        logger.info("気象データの取得処理を開始します。")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with open(output_filepath, "wb") as f:
            f.write(response.content)

        logger.info(f"正常にダウンロードしました: {output_filepath}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"【エラー】ダウンロードに失敗しました: {e}", exc_info=True)
        return False
