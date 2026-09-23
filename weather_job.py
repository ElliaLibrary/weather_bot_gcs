# envファイル読み込み
from dotenv import load_dotenv
load_dotenv()

# load_dotenv() の後に import する(各モジュールが環境変数を読むため)
from downloader import download_jma_csv
from data_insert import insert_weather_data
from send_gmail import send_gmail
from file_upload import upload_to_gcs

from pathlib import Path
from datetime import datetime,date
from zoneinfo import ZoneInfo
import os
import google.cloud.logging
import logging

# ==========================================
# ログの設定
# ==========================================
def setup_logging():
    """
    本番ではCloud Loggingへ、
    ローカル実行ではコンソールへログを出力する。
    """
    # K_SERVICE は Cloud Functions Gen2 / Cloud Run が自動で設定する環境変数
    if os.getenv("K_SERVICE"):
        client = google.cloud.logging.Client()
        client.setup_logging() 
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

setup_logging()
logger = logging.getLogger("weather_job")

# ------------------
# 変数取得
# ------------------
# 保存先：ローカルまたは /tmp/data
SAVE_DIR = os.environ["SAVE_DIR"]
output_dir_path = Path(SAVE_DIR)
output_dir_path.mkdir(parents=True, exist_ok=True)

# ダウンロードCSVファイル名
output_filepath = (output_dir_path / f"raw_pre24h00{date.today().strftime('%Y%m%d')}.csv")

# データ取得URL
DOWNLORD_URL = "https://www.data.jma.go.jp/stats/data/mdrr/pre_rct/alltable/pre24h00_rct.csv"

# ------------------
# ERRORログをメモリに溜める
# ------------------
class ErrorCollector(logging.Handler):
    """実行中に出た ERROR 以上のログ(スタックトレース込み)をメモリに溜める。"""
    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        self.messages = []

    def emit(self, record):
        self.messages.append(self.format(record))   # exc_info があればトレースも含まれる

# ------------------
# メイン処理
# ------------------
def run_main_process():
    logger.info("処理を開始します。")
    
    collector = ErrorCollector()            
    logging.getLogger().addHandler(collector) 
    
    try:
        detail = "処理が最後まで完了しませんでした"   # 最初は失敗扱い
        
        #-------------------------------
        # 1. CSVのダウンロード
        #-------------------------------
        try:
            if not download_jma_csv(DOWNLORD_URL,output_filepath):
                    detail = "CSVのダウンロードに失敗しました" 
                    return False
        except Exception as e:
            logger.error(f"CSVのダウンロード処理中に予期しない例外が発生しました: {e}", exc_info=True)
            detail = "CSVのダウンロード処理中に予期しない例外が発生しました"
            return False    
        # -------------------------------
        # ２. GCSアップロード
        # -------------------------------
        #クラウド実行の場合のみ
        if os.getenv("K_SERVICE"): 
            try:
                if not upload_to_gcs(output_filepath, f"data/{output_filepath.name}"):
                    detail = "GCSへのアップロードに失敗しました"
                    return False
            except Exception as e:
                logger.error(f"GCSへのアップロード処理中に予期しない例外が発生しました: {e}", exc_info=True)
                detail = "GCSへのアップロード処理中に予期しない例外が発生しました"
                return False   
        #-------------------------------
        # ３. テーブルへデータ登録
        #-------------------------------
        try:
            if not insert_weather_data(output_filepath):
                detail = "データベースへの登録とストアドの実行に失敗しました"
                return False
        except Exception as e:
            logger.error(f"データベース登録処理途中に予期しない例外が発生しました: {e}", exc_info=True)
            detail = "データベース登録処理途中に予期しない例外が発生しました"
            return False    
        
        detail = "" # すべて成功
        return True
    
    finally:
        logging.getLogger().removeHandler(collector) 
        
        logger.info("すべての処理を終了します。")
        #-------------------------------
        # ４. 結果をGmailで通知
        #-------------------------------
        if collector.messages:
            error_text = "\n\n".join(collector.messages)[:5000]  
            detail = f"{detail}\n\n--- エラーの内容 ---\n{error_text}"
            
            now_jst = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")
            detail = f"発生時刻(JST): {now_jst}\n{detail}"
            
        send_gmail(detail == "", detail)

if __name__ == "__main__":
    run_main_process()
