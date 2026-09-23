from datetime import datetime, timedelta
from google.cloud.sql.connector import Connector
import os
import pandas as pd
import sqlalchemy
import logging
from column_config import build_column_mapping

logger = logging.getLogger("insert_weather_data")

# 接続情報の定義
INSTANCE_CONNECTION_NAME =  os.environ["INSTANCE_CONNECTION_NAME"]
DB_USER =  os.environ["DB_USER"]
DB_PASSWORD =  os.environ["DB_PASSWORD"]
DB_DATABASE =  os.environ["DB_DATABASE"]

# 定数の定義
TABLE_NAME = "stg_jma_precipitation"
FUNCTION_NAME = "sp_load_dt_weather_data"

def insert_weather_data(output_filepath: str) -> bool:

    #-------------------------------------
    # １・ CSVファイル読み込み
    #-------------------------------------
    try:
        #CSVデータ格納
        df = pd.read_csv(output_filepath, encoding="cp932")

        # 当日と前日の日付を取得
        obs_year = int(df["現在時刻(年)"].iloc[0])
        obs_month = int(df["現在時刻(月)"].iloc[0])
        obs_day = int(df["現在時刻(日)"].iloc[0])
        
        # 当日日時
        current_date = datetime(obs_year, obs_month, obs_day)
        
        # 前日を算出
        prev_date = current_date - timedelta(days=1)
        prev_day = prev_date.day

        #CSVの項目名をデータベース側の列名にリネームする
        column_mapping = build_column_mapping(obs_month,obs_day, prev_day)
        df = df.rename(columns=column_mapping)
           
    except Exception as e:
        logger.error(f"【エラー】CSVファイルの読み込みに失敗しました: {e}", exc_info=True)
        # ここで処理を中断
        return False

    #-------------------------------------
    # 接続エンジン作成
    #-------------------------------------
    # コネクションを取得
    connector = Connector()
    getconn = lambda: connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_DATABASE,
    )
    # SQLAlchemyエンジンの作成
    engine = sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)
    
    step = "データベース接続"
    try:
        with engine.begin() as conn:
            
            #-------------------------------------
            # テーブルへのデータ登録
            #-------------------------------------                
            step = "テーブルへのデータ登録"
            
            df.to_sql(
                TABLE_NAME,
                con=conn,
                if_exists="append",
                index=False,
                chunksize=1000,
            )
            logger.info("テーブル登録が正常に完了しました")

            # -------------------------------------
            # 関数の実行
            # -------------------------------------
            step = "ストアド関数の実行"
            
            sql_query = sqlalchemy.text(f"SELECT {FUNCTION_NAME}()")
            conn.execute(sql_query)
            logger.info("ストアドの実行が正常に完了しました")
            
            step = "コミット"
            
        return True   
                    
    except Exception as e:
        logger.error(f"【エラー】{step}に失敗しました。処理を中断します。詳細: {e}", exc_info=True)
        return False
        
    #-------------------------------------
    # 終了
    #-------------------------------------
    finally:
        engine.dispose()
        connector.close()
        logger.info("データベース接続を閉じました。")