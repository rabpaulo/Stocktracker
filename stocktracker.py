#!/usr/bin/env python3
# If you dont want to keep activating venv, change the shebang to:
# !/path/to/your/venv/bin/python3

import yfinance as yf
import argparse
from colorama import Fore

parser = argparse.ArgumentParser(description="Stock Tracker")
parser.add_argument('-s', '--simple', help='Simple mode', action='store_true')
parser.add_argument('-f', '--find', nargs='?', const=True, help='Search for specific stock')
parser.add_argument('-l', '--list', action='store_true', help='List all stocks in the portfolio')
args = parser.parse_args()

acoes = [
    "PETR3.SA",
    "PETR4.SA", 
    "WEGE3.SA"
]

def get_info(acao):
    data = yf.Ticker(acao).history(period="1d", interval="1m")
    if not data.empty:
        return {
            "current": data['Close'].iloc[-1],
            "open": data['Open'].iloc[0],
            "high_24h": data['High'].max(),
            "low_24h": data['Low'].min(),
            "daily": data['Close'].iloc[-1] - data['Open'].iloc[0],
            "daily_percent": ((data['Close'].iloc[-1] - data['Open'].iloc[0]) / data['Open'].iloc[0]) * 100,
        }

def print_info(info, mode="simple"):
    if info is None:
        print(f"{Fore.RED}Error fetching data for {acao}{Fore.RESET}")
        return

    if mode == "simple":
        print(f"{Fore.CYAN}{acao.upper()}{Fore.RESET}: {info['current']:.2f} ")
    elif mode == "detailed":
        print(f"{Fore.CYAN}Ticker{Fore.RESET}: {acao.upper()}")
        print(f"Current Price: {info['current']:.2f}")
        print(f"Open Price: {info['open']:.2f}")
        print(f"24h High: {info['high_24h']:.2f}")
        print(f"24h Low: {info['low_24h']:.2f}")
        print(f"Daily Change: {info['daily']:.2f}")
        print(f"Daily Change (%): {info['daily_percent']:.2f}%")
        print("-" * 20)

if args.list:
    for acao in acoes:
        print(acao)
    exit(0)

mode = "detailed"
if args.simple:
    mode = "simple"

acao = ""
if args.find is True:
    acao = input("Enter the stock ticker: ")
elif args.find:
    acao = args.find
if acao: 
    print_info(get_info(acao), mode)
    exit(0)

for acao in acoes:
    print_info(get_info(acao), mode)
