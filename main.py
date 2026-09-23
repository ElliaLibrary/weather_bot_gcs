# Google Cloud側から呼び出される「トリガー用の関数」

import functions_framework
from weather_job import run_main_process  # 修正した main.py から main 関数をインポート

@functions_framework.http
def scheduled_job(request):
    """
    Cloud Scheduler / Cloud Run functions から呼び出されるエントリーポイント
    """
    # メイン処理の実行
    success = run_main_process()
    
    if success:
        return "Job executed successfully", 200
    else:
        return "Job failed, check logs for details", 500