# upbit auto trading bot
import time
import pyupbit
import datetime
import numpy as np
import requests
from dotenv import load_dotenv
import os 

# load .env
load_dotenv()

# upbit access, secret key
access = os.environ.get('ACCESS')

secret = os.environ.get('SECRET')

coin = os.environ.get('COIN')
fee = 0.05

# slack bot
myToken = os.environ.get('MYTOKEN')
myChannel = os.environ.get('MYCHANNEL')

def post_message(token, myChannel, text):
    # """슬랙 메시지 전송"""
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json; charset=utf-8"
    }
    data = {
        "channel": myChannel,
        "text": text
    }
    response = requests.post(url, headers=headers, json=data)
    assert response.status_code == 200
    return response.json()

def get_target_price(df, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_current_price(coin):
    """현재가 조회"""
    return pyupbit.get_orderbook(coin=coin)["orderbook_units"][0]["ask_price"]

def get_balance(coin):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == coin:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_start_time(coin):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(coin, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_ma10(coin):
    """10일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(coin, interval="day", count=10)
    ma10 = df['close'].rolling(10).mean().iloc[-1]
    return ma10

def get_ror(df, fee, K):
    """변동성 돌파 전략으로 수익률을 구한다."""
    df['range'] = (df['high'] - df['low']) * K
    df['target'] = df['open'] + df['range'].shift(1)

    df['ror'] = np.where(df['high'] > df['target'],df['close'] / df['target'] - fee,1)

    ror = df['ror'].cumprod()[-2]
    return ror

def find_k(coin, fee):
    df = pyupbit.get_ohlcv(coin, interval = "day", count = 10)
    max_crr = 0
    best_K = 0.5
    for k in np.arange(0.1, 1.0, 0.1) :
        crr = get_ror(df, fee, k)
        if crr > max_crr :
            max_crr = crr
            best_K = k
    print("best_K : ", best_K)
    return best_K

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time(coin)
        end_time = start_time + datetime.timedelta(days=1)

        if start_time < now < end_time - datetime.timedelta(seconds=10):
            # 전략
            df = pyupbit.get_ohlcv(coin, interval="day", count=2)
            target_price = get_target_price(df, find_k(coin, fee))
            time.sleep(1)

            # 10일 이동 평균값
            ma10 = get_ma10(coin)
            # 현재 가격
            current_price = pyupbit.get_current_price(coin)
            print("target_price : ", target_price, "/", 
            "current_price : ", current_price, "/",
            "ma10 : ", ma10, "/", 
            coin, " : ", (upbit.get_balance(coin) * current_price))

            if (target_price < current_price) and (current_price > ma10):
                krw = upbit.get_balance("KRW")
                if krw >= 5000:
                    upbit.buy_market_order(coin, krw*0.95)
                    post_message(myToken, myChannel, coin  + " : " + str(current_price))
        else:
            Crypto = upbit.get_balance(coin) * current_price;
            if Crypto > 5000:
                upbit.sell_market_order(coin, Crypto*0.95)
                post_message(myToken, myChannel, coin  + " : " + str(current_price))
        time.sleep(1.5)
    except Exception as e:
        print(e)
        time.sleep(1.5)