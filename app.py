"""
=============================================================
EMA 34 HIGH / LOW TELEGRAM ALERT BOT
NIFTY 50 + SENSEX

FYERS API V3 + TELEGRAM

DAILY FLOW
----------

08:50 AM IST:
    Bot sends FYERS login link to Telegram.

USER:
    Opens the link and completes FYERS login.

USER:
    Copies the complete redirected URL.

USER:
    Sends the complete URL to the Telegram bot.

BOT:
    Extracts auth_code.
    Generates FYERS access token.
    Starts live monitoring.

MARKET:
    09:15 AM to 03:15 PM IST

STRATEGY:
    5-minute candles

CALL:
    Close > Open
    AND
    Close > EMA 34 High

PUT:
    Close < Open
    AND
    Close < EMA 34 Low

ALTERNATION:
    First valid signal = CALL or PUT.

    After CALL:
        Ignore further CALL signals.
        Wait for PUT.

    After PUT:
        Ignore further PUT signals.
        Wait for CALL.

DAY ALLOCATION:
    Monday    -> NIFTY
    Tuesday   -> NIFTY
    Wednesday -> SENSEX
    Thursday  -> SENSEX
    Friday    -> NIFTY

NO ORDERS ARE PLACED.
ONLY TELEGRAM ALERTS ARE GENERATED.
=============================================================
"""
import os
import time
import traceback
import threading
from datetime import datetime, timedelta, time as dt_time
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from flask import Flask

from fyers_apiv3 import fyersModel


# ============================================================
# TIMEZONE
# ============================================================

IST = ZoneInfo("Asia/Kolkata")


# ============================================================
# USER CONFIGURATION
# ============================================================

# ------------------------------------------------------------
# FYERS CREDENTIALS
# ------------------------------------------------------------

CLIENT_ID = os.getenv("FYERS_CLIENT_ID")
SECRET_KEY = os.getenv("FYERS_SECRET_KEY")

# This should match the redirect URL configured
# in your FYERS application.
REDIRECT_URI = "https://www.google.com"


# ------------------------------------------------------------
# TELEGRAM CREDENTIALS
# ------------------------------------------------------------

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# ============================================================
# STRATEGY CONFIGURATION
# ============================================================

NIFTY_SYMBOL = "NSE:NIFTY50-INDEX"
SENSEX_SYMBOL = "BSE:SENSEX-INDEX"

NIFTY_NAME = "NIFTY 50"
SENSEX_NAME = "SENSEX"

RESOLUTION = "5"

EMA_LENGTH = 34


# ============================================================
# MARKET TIMINGS
# ============================================================

LOGIN_TIME = dt_time(8, 50)

MARKET_OPEN = dt_time(9, 15)
MARKET_CLOSE = dt_time(15, 15)

# Last candle starts at 15:10 and closes at 15:15.
LAST_CANDLE_START = dt_time(15, 10)


# ============================================================
# DAY ALLOCATION
# ============================================================

# Monday = 0
# Tuesday = 1
# Wednesday = 2
# Thursday = 3
# Friday = 4

NIFTY_DAYS = {0, 1, 4}
SENSEX_DAYS = {2, 3}


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if (
        TELEGRAM_BOT_TOKEN == "YOUR_NEW_TELEGRAM_BOT_TOKEN"
        or
        TELEGRAM_CHAT_ID == "YOUR_TELEGRAM_CHAT_ID"
    ):

        print("\nTELEGRAM NOT CONFIGURED")
        print(message)

        return False

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True
    }

    try:

        response = requests.post(
            url,
            data=payload,
            timeout=15
        )

        result = response.json()

        if (
            response.status_code == 200
            and result.get("ok")
        ):

            return True

        print("\nTELEGRAM ERROR:")
        print(result)

        return False

    except Exception as e:

        print("\nTELEGRAM CONNECTION ERROR:")
        print(e)

        return False


# ============================================================
# TELEGRAM UPDATE SYSTEM
# ============================================================

def get_telegram_updates(offset=None):

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/getUpdates"
    )

    params = {
        "timeout": 30
    }

    if offset is not None:

        params["offset"] = offset

    try:

        response = requests.get(
            url,
            params=params,
            timeout=40
        )

        result = response.json()

        if not result.get("ok"):

            print("\nTELEGRAM UPDATE ERROR:")
            print(result)

            return []

        return result.get("result", [])

    except Exception as e:

        print("\nTELEGRAM UPDATE CONNECTION ERROR:")
        print(e)

        return []


# ============================================================
# CLEAR OLD TELEGRAM UPDATES
# ============================================================

def get_latest_update_offset():

    updates = get_telegram_updates()

    if not updates:

        return None

    latest_id = updates[-1].get("update_id")

    if latest_id is None:

        return None

    return latest_id + 1


# ============================================================
# WAIT FOR FYERS REDIRECT URL
# ============================================================

def wait_for_fyers_redirect_url():

    print("\n" + "=" * 70)
    print("WAITING FOR FYERS REDIRECT URL ON TELEGRAM")
    print("=" * 70)

    send_telegram(
        "📩 Please complete your FYERS login.\n\n"
        "After login, your browser will redirect to "
        "the Google URL.\n\n"
        "Copy the COMPLETE redirected URL and send it "
        "directly to this Telegram bot."
    )

    # Ignore messages that were sent before
    # the current login process started.
    offset = get_latest_update_offset()

    while True:

        updates = get_telegram_updates(offset)

        for update in updates:

            update_id = update.get("update_id")

            if update_id is not None:

                offset = update_id + 1

            message = update.get("message")

            if not message:

                continue

            chat = message.get("chat", {})

            chat_id = str(
                chat.get("id", "")
            )

            # Security:
            # Accept messages only from your chat ID.
            if chat_id != str(TELEGRAM_CHAT_ID):

                continue

            text = message.get(
                "text",
                ""
            ).strip()

            if not text:

                continue

            # ------------------------------------------------
            # AUTH CODE DETECTED
            # ------------------------------------------------

            if "auth_code=" in text:

                print(
                    "\nFYERS REDIRECT URL RECEIVED."
                )

                send_telegram(
                    "🔄 Redirect URL received.\n"
                    "Generating FYERS access token..."
                )

                return text

            # ------------------------------------------------
            # HELP COMMAND
            # ------------------------------------------------

            if text.lower() in [
                "/start",
                "/login",
                "login"
            ]:

                send_telegram(
                    "Please complete the FYERS login "
                    "using the login link I sent.\n\n"
                    "Then send me the COMPLETE redirected URL "
                    "containing auth_code."
                )

            # ------------------------------------------------
            # INVALID MESSAGE
            # ------------------------------------------------

            else:

                send_telegram(
                    "⚠️ I am waiting for the FYERS "
                    "redirect URL.\n\n"
                    "Please send the COMPLETE URL "
                    "containing auth_code."
                )

        time.sleep(2)


# ============================================================
# FYERS LOGIN THROUGH TELEGRAM
# ============================================================

def fyers_login_telegram():

    print("\n" + "=" * 70)
    print("FYERS TELEGRAM LOGIN")
    print("=" * 70)

    if (
        CLIENT_ID == "YOUR_NEW_FYERS_CLIENT_ID"
        or
        SECRET_KEY == "YOUR_NEW_FYERS_SECRET_KEY"
    ):

        raise Exception(
            "FYERS credentials are not configured."
        )

    session = fyersModel.SessionModel(

        client_id=CLIENT_ID,

        secret_key=SECRET_KEY,

        redirect_uri=REDIRECT_URI,

        response_type="code",

        grant_type="authorization_code"
    )

    # Generate FYERS login URL.
    auth_url = session.generate_authcode()

    print("\nFYERS LOGIN URL:")
    print(auth_url)

    # Send the URL to Telegram.
    login_message = (
        "🌅 GOOD MORNING!\n\n"
        "🤖 Your EMA 34 Trading Alert Bot is ready.\n\n"
        "Please complete your FYERS login using "
        "the link below:\n\n"
        f"{auth_url}\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "After successful login:\n\n"
        "1️⃣ You will be redirected to Google.\n"
        "2️⃣ Copy the COMPLETE redirected URL.\n"
        "3️⃣ Send that URL to this Telegram bot.\n\n"
        "The bot will automatically start "
        "monitoring after successful authentication."
    )

    sent = send_telegram(
        login_message
    )

    if not sent:

        raise Exception(
            "Unable to send FYERS login URL "
            "through Telegram."
        )

    # Wait for the user to send
    # the redirected URL.
    full_url = (
        wait_for_fyers_redirect_url()
    )

    # ========================================================
    # EXTRACT AUTH CODE
    # ========================================================

    if "auth_code=" in full_url:

        auth_code = (
            full_url
            .split("auth_code=")[1]
            .split("&")[0]
        )

    else:

        auth_code = full_url.strip()

    if not auth_code:

        raise Exception(
            "FYERS auth_code was not found."
        )

    print("\nAUTH CODE RECEIVED.")
    print("Generating FYERS access token...")

    # Set authorization code.
    session.set_token(auth_code)

    # Generate access token.
    response = session.generate_token()

    if not response:

        raise Exception(
            "Empty response from FYERS."
        )

    if response.get("s") != "ok":

        print("\nFYERS LOGIN FAILED:")
        print(response)

        send_telegram(
            "❌ FYERS LOGIN FAILED.\n\n"
            "The access token could not be generated.\n\n"
            "Please wait for the next login cycle "
            "or restart the bot."
        )

        raise Exception(
            f"FYERS login failed: {response}"
        )

    access_token = response.get(
        "access_token"
    )

    if not access_token:

        raise Exception(
            "FYERS access token was not received."
        )

    print("\nFYERS LOGIN SUCCESSFUL.")

    # Create FYERS client.
    fyers = fyersModel.FyersModel(

        client_id=CLIENT_ID,

        token=access_token,

        is_async=False,

        log_path=""
    )

    send_telegram(
        "✅ FYERS LOGIN SUCCESSFUL!\n\n"
        "🤖 EMA 34 Alert Bot is now ACTIVE.\n\n"
        "📊 The bot will monitor the market "
        "and send valid alternating signals."
    )

    return fyers


# ============================================================
# SYMBOL HELPERS
# ============================================================

def get_symbol_name(symbol):

    if symbol == NIFTY_SYMBOL:

        return NIFTY_NAME

    if symbol == SENSEX_SYMBOL:

        return SENSEX_NAME

    return symbol


def is_allowed_day(
    symbol,
    trading_date
):

    weekday = trading_date.weekday()

    if symbol == NIFTY_SYMBOL:

        return weekday in NIFTY_DAYS

    if symbol == SENSEX_SYMBOL:

        return weekday in SENSEX_DAYS

    return False


# ============================================================
# FETCH HISTORY
# ============================================================

def fetch_history(

    fyers,

    symbol,

    start_date,

    end_date
):

    all_candles = []

    current_start = start_date

    # Download data in chunks.
    chunk_days = 60

    while current_start <= end_date:

        current_end = min(

            current_start
            + timedelta(
                days=chunk_days - 1
            ),

            end_date
        )

        request_data = {

            "symbol": symbol,

            "resolution": RESOLUTION,

            "date_format": "1",

            "range_from":
                current_start.strftime(
                    "%Y-%m-%d"
                ),

            "range_to":
                current_end.strftime(
                    "%Y-%m-%d"
                ),

            "cont_flag": "1"
        }

        print(
            f"Downloading "
            f"{get_symbol_name(symbol)} | "
            f"{current_start} -> {current_end}"
        )

        try:

            response = fyers.history(
                data=request_data
            )

        except Exception as e:

            print(
                "\nFYERS HISTORY ERROR:"
            )

            print(e)

            raise

        if not response:

            print(
                "Empty FYERS response."
            )

        elif response.get("s") != "ok":

            print(
                "\nFYERS HISTORY ERROR:"
            )

            print(response)

        else:

            candles = response.get(
                "candles",
                []
            )

            if candles:

                all_candles.extend(
                    candles
                )

        current_start = (
            current_end
            + timedelta(days=1)
        )

    # ========================================================
    # EMPTY DATAFRAME
    # ========================================================

    if not all_candles:

        return pd.DataFrame(
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "datetime"
            ]
        )

    # ========================================================
    # DATAFRAME
    # ========================================================

    df = pd.DataFrame(

        all_candles,

        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]
    )

    # Remove duplicates.
    df = df.drop_duplicates(
        subset=["timestamp"]
    )

    # Convert timestamps to IST.
    df["datetime"] = (
        pd.to_datetime(

            df["timestamp"],

            unit="s",

            utc=True

        )
        .dt.tz_convert(
            "Asia/Kolkata"
        )
        .dt.tz_localize(None)
    )

    df = (

        df

        .sort_values("datetime")

        .reset_index(drop=True)
    )

    return df


# ============================================================
# EMA CALCULATION
# ============================================================

def calculate_ema(df):

    df = df.copy()

    df["EMA_High"] = (

        df["high"]

        .ewm(

            span=EMA_LENGTH,

            adjust=False,

            min_periods=EMA_LENGTH

        )

        .mean()
    )

    df["EMA_Low"] = (

        df["low"]

        .ewm(

            span=EMA_LENGTH,

            adjust=False,

            min_periods=EMA_LENGTH

        )

        .mean()
    )

    return df


# ============================================================
# VALID MARKET CANDLE
# ============================================================

def is_valid_candle_start(
    candle_datetime
):

    candle_time = (
        candle_datetime.time()
    )

    return (

        MARKET_OPEN

        <= candle_time

        <= LAST_CANDLE_START
    )


# ============================================================
# LIVE STATE
# ============================================================

class LiveState:

    def __init__(self):

        self.state = {

            NIFTY_SYMBOL:
                "NEUTRAL",

            SENSEX_SYMBOL:
                "NEUTRAL"
        }

        self.current_date = {

            NIFTY_SYMBOL:
                None,

            SENSEX_SYMBOL:
                None
        }

        self.last_processed_candle = {

            NIFTY_SYMBOL:
                None,

            SENSEX_SYMBOL:
                None
        }


    def reset_for_new_day(

        self,

        symbol,

        trading_date
    ):

        if (
            self.current_date[symbol]
            != trading_date
        ):

            self.current_date[
                symbol
            ] = trading_date

            self.state[
                symbol
            ] = "NEUTRAL"

            self.last_processed_candle[
                symbol
            ] = None


# ============================================================
# CHECK LIVE SYMBOL
# ============================================================

def check_live_symbol(

    fyers,

    symbol,

    live_state
):

    now = datetime.now(IST)

    trading_date = now.date()

    # ========================================================
    # DAY ALLOCATION
    # ========================================================

    if not is_allowed_day(

        symbol,

        trading_date
    ):

        return

    # ========================================================
    # DAILY RESET
    # ========================================================

    live_state.reset_for_new_day(

        symbol,

        trading_date
    )

    # ========================================================
    # EMA WARMUP DATA
    # ========================================================

    warmup_start = (

        trading_date

        - timedelta(days=60)
    )

    df = fetch_history(

        fyers,

        symbol,

        warmup_start,

        trading_date
    )

    if df.empty:

        print(
            f"{get_symbol_name(symbol)}: "
            "No candle data."
        )

        return

    # ========================================================
    # CALCULATE EMA
    # ========================================================

    df = calculate_ema(df)

    # ========================================================
    # TODAY ONLY
    # ========================================================

    df["date"] = (
        df["datetime"].dt.date
    )

    df = df[
        df["date"] == trading_date
    ].copy()

    # ========================================================
    # VALID MARKET CANDLES
    # ========================================================

    df = df[
        df["datetime"].apply(
            is_valid_candle_start
        )
    ].copy()

    if df.empty:

        return

    # ========================================================
    # FULLY CLOSED CANDLES ONLY
    # ========================================================

    now_naive = (
        now.replace(tzinfo=None)
    )

    df["close_datetime"] = (

        df["datetime"]

        + timedelta(minutes=5)
    )

    df = df[
        df["close_datetime"]
        <= now_naive
    ].copy()

    if df.empty:

        return

    # ========================================================
    # LATEST CLOSED CANDLE
    # ========================================================

    latest = df.iloc[-1]

    candle_start = (
        latest["datetime"]
    )

    # ========================================================
    # DUPLICATE PROTECTION
    # ========================================================

    if (
        live_state.last_processed_candle[
            symbol
        ]
        == candle_start
    ):

        return

    live_state.last_processed_candle[
        symbol
    ] = candle_start

    # ========================================================
    # EMA
    # ========================================================

    ema_high = (
        latest["EMA_High"]
    )

    ema_low = (
        latest["EMA_Low"]
    )

    if (

        pd.isna(ema_high)

        or

        pd.isna(ema_low)
    ):

        print(
            f"{get_symbol_name(symbol)}: "
            "EMA not ready."
        )

        return

    # ========================================================
    # PRICES
    # ========================================================

    open_price = float(
        latest["open"]
    )

    close_price = float(
        latest["close"]
    )

    # ========================================================
    # STRATEGY CONDITIONS
    # ========================================================

    call_condition = (

        close_price > open_price

        and

        close_price > ema_high
    )

    put_condition = (

        close_price < open_price

        and

        close_price < ema_low
    )

    # ========================================================
    # CURRENT STATE
    # ========================================================

    current_state = (
        live_state.state[symbol]
    )

    signal = None

    # ========================================================
    # NEUTRAL
    # ========================================================

    if current_state == "NEUTRAL":

        if call_condition:

            signal = "CALL"

            live_state.state[
                symbol
            ] = "CALL"

        elif put_condition:

            signal = "PUT"

            live_state.state[
                symbol
            ] = "PUT"

    # ========================================================
    # CURRENT STATE = CALL
    # ========================================================

    elif current_state == "CALL":

        # Ignore further CALL.
        # Only PUT can be accepted.

        if put_condition:

            signal = "PUT"

            live_state.state[
                symbol
            ] = "PUT"

    # ========================================================
    # CURRENT STATE = PUT
    # ========================================================

    elif current_state == "PUT":

        # Ignore further PUT.
        # Only CALL can be accepted.

        if call_condition:

            signal = "CALL"

            live_state.state[
                symbol
            ] = "CALL"

    # ========================================================
    # NO SIGNAL
    # ========================================================

    if signal is None:

        print(
            f"[{now.strftime('%H:%M:%S')}] "
            f"{get_symbol_name(symbol)} | "
            f"State={live_state.state[symbol]} | "
            f"No alternating signal"
        )

        return

    # ========================================================
    # SIGNAL ACCEPTED
    # ========================================================

    close_datetime = (

        candle_start

        + timedelta(minutes=5)
    )

    if signal == "CALL":

        direction = "Bullish"

    else:

        direction = "Bearish"

    message = (

        "🚨 EMA 34 SIGNAL\n\n"

        f"Index: "
        f"{get_symbol_name(symbol)}\n"

        f"Time: "
        f"{close_datetime.strftime('%H:%M:%S')}\n"

        f"Signal: "
        f"{direction} ({signal})\n"

        f"Close Price: "
        f"{close_price:.2f}\n"

        f"EMA 34 High: "
        f"{float(ema_high):.2f}\n"

        f"EMA 34 Low: "
        f"{float(ema_low):.2f}\n"

        f"Current State: "
        f"{live_state.state[symbol]}"
    )

    print("\n" + "=" * 70)
    print("VALID ALTERNATING SIGNAL")
    print("=" * 70)

    print(message)

    print("=" * 70)

    if send_telegram(message):

        print(
            "Telegram alert sent."
        )

    else:

        print(
            "Telegram alert failed."
        )


# ============================================================
# GET NEXT 5-MINUTE CHECK
# ============================================================

def get_next_check_time():

    now = datetime.now(IST)

    minute = now.minute

    next_minute = (

        (minute // 5 + 1) * 5
    )

    if next_minute >= 60:

        target = (

            now.replace(

                minute=0,

                second=5,

                microsecond=0

            )

            + timedelta(hours=1)
        )

    else:

        target = now.replace(

            minute=next_minute,

            second=5,

            microsecond=0
        )

    # If current time is exactly at
    # a candle-check boundary before second 5.
    if (

        now.minute % 5 == 0

        and

        now.second < 5
    ):

        target = now.replace(

            second=5,

            microsecond=0
        )

    return target


# ============================================================
# LIVE MARKET SESSION
# ============================================================

def run_live(fyers):

    print("\n" + "=" * 70)
    print("LIVE TELEGRAM ALERT MODE")
    print("=" * 70)

    now = datetime.now(IST)

    weekday = now.weekday()

    # ========================================================
    # SELECT TODAY'S INDEX
    # ========================================================

    if weekday in NIFTY_DAYS:

        active_symbol = NIFTY_SYMBOL

    elif weekday in SENSEX_DAYS:

        active_symbol = SENSEX_SYMBOL

    else:

        print(
            "Today is not a trading day."
        )

        return

    send_telegram(
        "📊 LIVE MONITORING STARTED\n\n"
        f"Index: {get_symbol_name(active_symbol)}\n"
        "Timeframe: 5 Minutes\n"
        "Strategy: EMA 34 High / Low\n\n"
        "I will send alerts only for "
        "valid alternating signals."
    )

    state = LiveState()

    while True:

        try:

            now = datetime.now(IST)

            # ====================================================
            # BEFORE MARKET
            # ====================================================

            if now.time() < MARKET_OPEN:

                target = now.replace(

                    hour=9,

                    minute=15,

                    second=5,

                    microsecond=0
                )

                sleep_seconds = (
                    target - now
                ).total_seconds()

                print(
                    f"Waiting for market open: "
                    f"{target.strftime('%H:%M:%S')}"
                )

                if sleep_seconds > 0:

                    time.sleep(
                        sleep_seconds
                    )

                continue

            # ====================================================
            # AFTER MARKET
            # ====================================================

            if now.time() > dt_time(
                15,
                15,
                10
            ):

                print(
                    "\nMARKET CLOSED."
                )

                send_telegram(
                    "🏁 MARKET CLOSED\n\n"
                    "Today's EMA 34 monitoring "
                    "session has finished.\n\n"
                    "The bot will send a new FYERS "
                    "login link before the next "
                    "trading session."
                )

                # IMPORTANT:
                # Return to main().
                # Main() will schedule tomorrow's login.
                return

            # ====================================================
            # WAIT FOR NEXT CANDLE CHECK
            # ====================================================

            target = (
                get_next_check_time()
            )

            print(
                f"\nNext candle check: "
                f"{target.strftime('%H:%M:%S')}"
            )

            sleep_seconds = (
                target
                - datetime.now(IST)
            ).total_seconds()

            if sleep_seconds > 0:

                time.sleep(
                    sleep_seconds
                )

            # ====================================================
            # CHECK ACTIVE INDEX
            # ====================================================

            check_live_symbol(

                fyers,

                active_symbol,

                state
            )

        except KeyboardInterrupt:

            print(
                "\nLive mode stopped."
            )

            return

        except Exception as e:

            print(
                "\nLIVE ERROR:"
            )

            print(e)

            traceback.print_exc()

            send_telegram(
                "⚠️ LIVE BOT ERROR\n\n"
                f"{str(e)}\n\n"
                "Retrying in 30 seconds..."
            )

            time.sleep(30)


# ============================================================
# GET NEXT LOGIN DATETIME
# ============================================================

def get_next_login_datetime():

    now = datetime.now(IST)

    target = now.replace(

        hour=LOGIN_TIME.hour,

        minute=LOGIN_TIME.minute,

        second=0,

        microsecond=0
    )

    # If today's login time has already passed,
    # start from tomorrow.
    if now >= target:

        target += timedelta(days=1)

    # Skip Saturday and Sunday.
    while target.weekday() >= 5:

        target += timedelta(days=1)

    return target


# ============================================================
# WAIT UNTIL DAILY LOGIN TIME
# ============================================================

def wait_until_login_time():

    target = (
        get_next_login_datetime()
    )

    print("\n" + "=" * 70)
    print(
        "NEXT FYERS LOGIN TIME"
    )
    print("=" * 70)

    print(
        target.strftime(
            "%A, %d %B %Y | %H:%M:%S IST"
        )
    )

    while True:

        now = datetime.now(IST)

        remaining = (
            target - now
        ).total_seconds()

        if remaining <= 0:

            break

        # Print status occasionally,
        # but don't wake unnecessarily every second.
        if remaining > 3600:

            time.sleep(300)

        elif remaining > 300:

            time.sleep(60)

        else:

            time.sleep(5)

    print(
        "\nLOGIN TIME REACHED."
    )


# ============================================================
# MAIN 24/7 BOT
# ============================================================

def main():

    print("\n" + "=" * 70)
    print(
        "EMA 34 HIGH / LOW"
    )
    print(
        "24/7 TELEGRAM ALERT BOT"
    )
    print("=" * 70)

    print(
        "\nBot is running continuously."
    )

    print(
        "FYERS login will be requested "
        "every trading day at 08:50 AM IST."
    )

    # ========================================================
    # INITIAL TELEGRAM TEST
    # ========================================================

    send_telegram(
        "🤖 EMA 34 Trading Bot Started\n\n"
        "The server is running continuously.\n"
        "I will send the FYERS login link "
        "at approximately 08:50 AM IST "
        "on the next trading day."
    )

    # ========================================================
    # 24/7 LOOP
    # ========================================================

    while True:

        try:

            # ------------------------------------------------
            # WAIT FOR 08:50 AM
            # ------------------------------------------------

            wait_until_login_time()

            # ------------------------------------------------
            # FYERS LOGIN THROUGH TELEGRAM
            # ------------------------------------------------

            fyers = (
                fyers_login_telegram()
            )

            # ------------------------------------------------
            # START LIVE SESSION
            # ------------------------------------------------

            run_live(fyers)

            # ------------------------------------------------
            # LIVE SESSION RETURNS AFTER MARKET CLOSE.
            # LOOP CONTINUES.
            # ------------------------------------------------

            print(
                "\nDaily session completed."
            )

            print(
                "Preparing for next login cycle..."
            )

            time.sleep(10)

        except KeyboardInterrupt:

            print(
                "\n\nBOT STOPPED MANUALLY."
            )

            send_telegram(
                "🛑 EMA 34 Trading Bot "
                "was stopped manually."
            )

            break

        except Exception as e:

            print(
                "\nMAIN ERROR:"
            )

            print(e)

            traceback.print_exc()

            send_telegram(
                "⚠️ BOT ERROR\n\n"
                f"{str(e)}\n\n"
                "The bot will retry automatically."
            )

            # Prevent rapid crash/restart loops.
            time.sleep(60)

# ============================================================
# FLASK HEALTH SERVER
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():

    return {
        "status": "online",
        "service": "EMA 34 Trading Bot"
    }


@app.route("/health")
def health():

    return {
        "status": "healthy",
        "bot": "running"
    }


def run_web_server():

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
    
# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":
    print(
        "Starting EMA Trading Bot..."
    )

    # Start trading bot in background thread.
    bot_thread = threading.Thread(
        target=main,
        daemon=True
    )

    bot_thread.start()

    # Start Flask web server.
    run_web_server()