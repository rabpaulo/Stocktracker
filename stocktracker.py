#!/usr/bin/env python3
# If you dont want to keep activating venv, change the shebang to:
# !/path/to/your/venv/bin/python3

import yfinance as yf
import argparse
import matplotlib.pyplot as plt

# Definir todas as flags possiveis
parser = argparse.ArgumentParser(description="Stock Tracker")
parser.add_argument('-s', '--simple',  action='store_true', help='Simple printing mode')
parser.add_argument('-l', '--list', action='store_true', help='List all stocks in the portfolio')
parser.add_argument('-f', '--find', nargs='?', const=True, help='Search for specific stock')
parser.add_argument('-p', '--plot', nargs='?', const=True, help='Generate a plot for the stock')
args = parser.parse_args()

ativos = [
    "PETR4.SA",
    "BBAS3.SA",
    "BTC-USD"
]

def get_info(ativo):
    data = yf.Ticker(ativo).history(period="1d", interval="1m")
    if not data.empty:
        info = {
            "current": data['Close'].iloc[-1],
            "open": data['Open'].iloc[0],
            "high_24h": data['High'].max(),
            "low_24h": data['Low'].min(),
            "daily": data['Close'].iloc[-1] - data['Open'].iloc[0],
            "daily_percent": ((data['Close'].iloc[-1] - data['Open'].iloc[0]) / data['Open'].iloc[0]) * 100,
            "raw_data": data
        }
        return info

def print_info(info, mode):
    if info is None:
        print(f"Error fetching data for {ativo}")
        return

    if mode == "simple":
        print(f"{ativo.upper().split('.')[0]}: {info['current']:.2f} ")
    else:
        print(f"Ticker: {ativo.upper()}")
        print(f"Current Price: {info['current']:.2f}")
        print(f"Open Price: {info['open']:.2f}")
        print(f"24h High: {info['high_24h']:.2f}")
        print(f"24h Low: {info['low_24h']:.2f}")
        print(f"Daily Change: {info['daily']:.2f}")
        print(f"Daily Change (%): {info['daily_percent']:.2f}%")
        print("-" * 20)

def plot_price(data, ticker):
    plt.figure(figsize=(10, 4))
    plt.plot(data.index, data['Close'], label='Preço de Fechamento')
    plt.title(f'Variação intradiária: {ticker}')
    plt.xlabel('Hora')
    plt.ylabel('Preço (R$)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def print_stocks():
    for ativo in ativos:
        print(ativo)
# List
if args.list:
    print_stocks()
    exit(0)
    
# Printing mode
mode = "simple" if args.simple else "detailed"

# Find
ativo = None

if args.find is True:
    ativo = input("Enter the stock ticker: ")
elif args.find:
    ativo = args.find
if ativo: 
    ativo = ativo.upper() + ".SA" if not ativo.endswith(".SA") else ativo
    print_info(get_info(ativo), mode)
    exit(0)

# Plot
if args.plot is True:
    ativo = input("Enter stock to generate the plot: ")
elif args.plot:
    ativo = args.plot
if ativo:
    ativo = ativo.upper() + ".SA" if not ativo.endswith(".SA") else ativo
    info = get_info(ativo)
    if info:
        plot_price(info['raw_data'], ativo)
    exit(0)
for ativo in ativos:
    print_info(get_info(ativo), mode)
