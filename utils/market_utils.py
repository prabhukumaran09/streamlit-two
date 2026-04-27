from datetime import datetime
import pytz

def is_market_open() -> bool:
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close

def get_market_status():
    if is_market_open():
        return "OPEN", "#3fb950"
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    if now.weekday() >= 5:
        return "WEEKEND", "#d29922"
    if now.hour < 9 or (now.hour == 9 and now.minute < 15):
        return "PRE-MARKET", "#d29922"
    return "CLOSED", "#f85149"
