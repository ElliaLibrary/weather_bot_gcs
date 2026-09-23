
"""テンプレートの {obs_month} / {obs_day} / {prev_day} を、引数の値で置き換えた項目名の辞書を作成する。"""
"""左側はCSVファイルの項目名、右側はテーブルの項目名"""

#CSVの項目名をデータベース側の列名にリネームする
COLUMN_MAPPING_TEMPLATE = {
    "観測所番号": "station_id",
    "都道府県": "prefecture",
    "地点": "station_name",
    "国際地点番号": "inter_station_id",
    "現在時刻(年)": "obs_year",
    "現在時刻(月)": "obs_month",
    "現在時刻(日)": "obs_day",
    "現在時刻(時)": "obs_hour",
    "現在時刻(分)": "obs_minute",
    "現在値(mm)": "current_value",
    "現在値の品質情報": "current_quality",
    # --- 日付によって変動する当日分 ---
    "{obs_day}日の最大値(mm)": "max_value",
    "{obs_day}日の最大値の品質情報": "max_quality",
    "{obs_day}日の最大値起時（時）(まで)": "max_time_hour",
    "{obs_day}日の最大値起時（分）(まで)": "max_time_minute",
    "{obs_day}日の最大値起時(まで)の品質情報": "max_time_quality",
    "極値更新": "extreme_update",
    "10年未満での極値更新": "extreme_update_under10y",
    # --- 厳密に計算された前日分 ---
    "{prev_day}日までの観測史上1位の値(mm)": "record_1st_value",
    "{prev_day}日までの観測史上1位の値の品質情報": "record_1st_quality",
    "{prev_day}日までの観測史上1位の値の年": "record_1st_year",
    "{prev_day}日までの観測史上1位の値の月": "record_1st_month",
    "{prev_day}日までの観測史上1位の値の日": "record_1st_day",

    "{prev_day}日までの{obs_month}月の1位の値(mm)": "sep_value",
    "{prev_day}日までの{obs_month}月の1位の値の品質情報": "sep_quality",
    "{prev_day}日までの{obs_month}月の1位の値の年": "sep_year",
    "{prev_day}日までの{obs_month}月の1位の値の月": "sep_month",
    "{prev_day}日までの{obs_month}月の1位の値の日": "sep_day",
    "統計開始年": "start_year",
    "imported_at": "imported_at" 
}

def build_column_mapping(obs_month: int, obs_day: int, prev_day: int) -> dict[str, str]:
    """テンプレートの {obs_month} / {obs_day} / {prev_day} を、引数の値で置き換えた辞書を返す。"""
    return {
        csv_column.format(obs_month=obs_month, obs_day=obs_day, prev_day=prev_day): db_column
        for csv_column, db_column in COLUMN_MAPPING_TEMPLATE.items()
    }