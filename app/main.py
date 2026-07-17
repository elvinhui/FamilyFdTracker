import schedule
import time
from datetime import datetime, timedelta
from db import DynamoDBHandler
from notifier import Notifier
from analytics import AnalyticsEngine

db = DynamoDBHandler()
notifier = Notifier()
engine = AnalyticsEngine()

def check_maturing_deposits():
    print(f"[{datetime.now()}] Running daily check for maturing deposits...")
    
    today = datetime.now().date()
    target_dates = {
        0: today,
        3: today + timedelta(days=3),
        7: today + timedelta(days=7)
    }

    for days_left, target_date in target_dates.items():
        date_str = target_date.strftime("%Y-%m-%d")
        maturing_items = db.get_deposits_by_maturity_date(date_str)
        
        if maturing_items:
            print(f"Found {len(maturing_items)} deposits maturing in {days_left} days ({date_str})")
            
            for item in maturing_items:
                msg = notifier.format_message(
                    bank_code=item.get('bank_code', 'Unknown'),
                    account_tail=item.get('account_tail', '****'),
                    interest_rate=item.get('interest_rate', '0.0'),
                    days_left=days_left
                )
                notifier.send_telegram_alert(msg)
                time.sleep(1) # Small delay to avoid hitting rate limits

def run_scheduler():
    # Schedule the check to run every day at 09:00 AM
    schedule.every().day.at("09:00").do(check_maturing_deposits)
    
    print("Scheduler started. Waiting for jobs...")
    
    # For testing purposes, uncomment the line below to run it immediately on startup
    # check_maturing_deposits()
    
    while True:
        schedule.run_pending()
        time.sleep(60) # Wait a minute before checking schedule again

if __name__ == "__main__":
    run_scheduler()
