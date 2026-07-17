import os
import urllib.request
import urllib.parse
import json

class Notifier:
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.chat_id = os.getenv('CHAT_ID')

    def format_message(self, bank_code, account_tail, interest_rate, days_left):
        if days_left == 0:
            time_str = "TODAY"
        else:
            time_str = f"in {days_left} days"

        return (
            f"🔔 *Fixed Deposit Reminder*\n\n"
            f"Your *{bank_code}* FD (account {account_tail}) matures *{time_str}*!\n\n"
            f"Current Rate: {interest_rate}%\n"
            f"Please review for renewal or withdrawal."
        )

    def send_telegram_alert(self, message: str):
        if not self.bot_token or not self.chat_id:
            print("Telegram credentials not configured. Skipping notification.")
            print(f"Message would have been: \n{message}")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        req = urllib.request.Request(url)
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        jsondata = json.dumps(data).encode('utf-8')
        
        try:
            response = urllib.request.urlopen(req, jsondata)
            if response.status == 200:
                print("Successfully sent Telegram alert.")
                return True
            else:
                print(f"Failed to send alert. Status code: {response.status}")
                return False
        except Exception as e:
            print(f"Error sending Telegram alert: {e}")
            return False
