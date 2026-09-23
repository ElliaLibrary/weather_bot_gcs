import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.message import EmailMessage
import os
import logging
from datetime import datetime 
from zoneinfo import ZoneInfo

GMAIL_REFRESH_TOKEN = os.environ["GMAIL_REFRESH_TOKEN"]
GMAIL_CLIENT_ID = os.environ["GMAIL_CLIENT_ID"]
GMAIL_CLIENT_SECRET = os.environ["GMAIL_CLIENT_SECRET"]
MAIL_ADRESS = os.environ["MAIL_ADRESS"]
SENDER_MAIL_ADRESS = os.environ["SENDER_MAIL_ADRESS"]
GMAIL_TOKEN_URI = "https://oauth2.googleapis.com/token"

logger = logging.getLogger("send_gmail")

def get_gmail_service():
    creds = Credentials(
        token=None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET,
        token_uri=GMAIL_TOKEN_URI,
    )
    return build("gmail", "v1", credentials=creds)

def send_notification(subject: str, body: str) -> None:
    service = get_gmail_service()
   
    message = EmailMessage()
    message["to"] = MAIL_ADRESS
    message["from"] = SENDER_MAIL_ADRESS
    message["subject"] = subject
    message.set_content(body)  
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()

def send_gmail(success:bool,detail:str="") -> None:
    try:
        today = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d") 
        if success:
            send_notification(f"バッチ処理完了{today}", "気象データの取り込みが完了しました。")
        else:
            send_notification(f"【エラー】バッチ処理失敗{today}", f"処理に失敗しました。\n{detail}")

        logger.info("Gmail送信が完了しました。")
        
    except Exception as e:
        # 失敗の原因は多くの場合認証や通信の問題なので、処理を中断せずにログに記録するだけにする
        logger.error(f"【エラー】Gmail送信に失敗しました: {e}", exc_info=True)
        