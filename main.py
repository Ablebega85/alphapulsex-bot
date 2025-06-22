#!/usr/bin/env python3

""" AlphaPulseX AI Bot - OKX Version with Real Signals + Groq AI + Telegram """

import time import json import requests import threading from datetime import datetime, timedelta from bs4 import BeautifulSoup import os

=== CONFIGURATION ===

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") GROQ_API_KEY = os.getenv("GROQ_API_KEY") AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", 90.0)) HEADERS = {"Authorization": f"Bearer {GROQ_API_KEY}"} TRADES_FILE = "trades.json"

=== TELEGRAM ===

def send_telegram(text, reply_to=None): data = {"chat_id": CHAT_ID, "text": text} if reply_to: data["reply_to_message_id"] = reply_to try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=data) except Exception as e: print("Telegram error:", e)

=== AI DECISION ===

def gpt_check_trade(data): try: payload = { "model": "llama3-70b-8192", "messages": [ {"role": "system", "content": "Will this futures/perpetual trade win? Answer YES or NO with confidence like 'YES - 95%'"}, {"role": "user", "content": json.dumps(data)} ] } r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=HEADERS, json=payload) resp = r.json()["choices"][0]["message"]["content"] res, score = resp.split("-") return (res.strip().upper() == "YES", float(score.strip().strip("%"))) except: return (False, 0.0)

=== DATA SOURCES ===

def fetch_okx_futures(): url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP" res = requests.get(url).json() return set(i["instId"].split("-")[0] for i in res.get("data", []))

def fetch_top_gecko(): url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=100" res = requests.get(url).json() return [{"pair": coin["symbol"].upper() + "USDT", "price": coin["current_price"]} for coin in res]

def fetch_dexscreener_trending(): res = requests.get("https://api.dexscreener.com/latest/dex/pairs").json() tokens = [] for p in res.get("pairs", [])[:10]: symbol = p["baseToken"]["symbol"] price = float(p["priceUsd"]) tokens.append({ "token": symbol.upper(), "entry": price, "target": price * 3, "stop": price * 0.5 }) return tokens

=== GPT CHAT LISTENER ===

def ask_gpt(user_input): try: payload = { "model": "llama3-70b-8192", "messages": [ {"role": "system", "content": "You are AlphaPulseX AI, a pro crypto trader."}, {"role": "user", "content": user_input} ] } r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=HEADERS, json=payload) return r.json()["choices"][0]["message"]["content"] except: return "⚠️ GPT error."

def chat_listener(): offset = None while True: try: qs = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", params={"timeout": 60, "offset": offset}).json()["result"] for u in qs: offset = u["update_id"] + 1 msg = u.get("message", {}) if msg.get("chat", {}).get("id") == int(CHAT_ID) and "text" in msg: resp = ask_gpt(msg["text"]) send_telegram(resp, reply_to=msg["message_id"]) except: pass time.sleep(2)

=== TRADE LOGIC ===

def save_trade(tr): with open(TRADES_FILE, "a") as f: f.write(json.dumps(tr) + "\n")

def check_results(): if not os.path.exists(TRADES_FILE): return out = [] lines = open(TRADES_FILE).read().splitlines() for l in lines: t = json.loads(l) if t["status"] == "pending" and datetime.utcnow() - datetime.fromisoformat(t["time"]) > timedelta(hours=1): if t.get("target") and t.get("entry"): current_price = float(t["entry"]) * 1.5  # Simulated current price result = "WIN" if current_price >= float(t["target"]) else "LOSS" send_telegram(f"📊 Result ({result})\n{t.get('token') or t.get('pair')}\nConfidence: {t['confidence']}%\nPosted: {t['time']}") t["status"] = result.lower() out.append(t)
