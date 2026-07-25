#!/usr/bin/env python3
# If you dont want to keep activating venv, change the shebang to:
# !/path/to/your/venv/bin/python3

import yfinance as yf
import argparse

TIME_RANGES = {
    "1d": {"period": "1d", "interval": "1m", "date_format": "%H:%M"},
    "1w": {"period": "7d", "interval": "30m", "date_format": "%d/%m"},
    "1m": {"period": "1mo", "interval": "1d", "date_format": "%d/%m"},
    "1y": {"period": "1y", "interval": "1wk", "date_format": "%m/%Y"},
}

# Definir todas as flags possiveis
parser = argparse.ArgumentParser(description="Stock Tracker")
parser.add_argument('-s', '--simple',  action='store_true', help='Simple printing mode')
parser.add_argument('-l', '--list', action='store_true', help='List all stocks in the portfolio')
parser.add_argument('-f', '--find', nargs='?', const=True, help='Search for specific stock')
parser.add_argument('-p', '--plot', nargs='?', const=True, help='Generate a CLI plot for the stock')
parser.add_argument(
    '-t',
    '--time',
    choices=TIME_RANGES,
    default='1d',
    help='Time range for stock data (default: 1d)',
)
args = parser.parse_args()

ativos = [
    "PETR4.SA",
    "BBAS3.SA",
    "BTC-USD"
]

def get_info(ativo, time_range):
    history_options = TIME_RANGES[time_range]
    data = yf.Ticker(ativo).history(
        period=history_options["period"],
        interval=history_options["interval"],
    )
    if not data.empty:
        change = data['Close'].iloc[-1] - data['Open'].iloc[0]
        info = {
            "current": data['Close'].iloc[-1],
            "start": data['Open'].iloc[0],
            "high": data['High'].max(),
            "low": data['Low'].min(),
            "change": change,
            "change_percent": (change / data['Open'].iloc[0]) * 100,
            "time_range": time_range,
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
        print(f"Time Range: {info['time_range']}")
        print(f"Current Price: {info['current']:.2f}")
        print(f"Start Price: {info['start']:.2f}")
        print(f"Range High: {info['high']:.2f}")
        print(f"Range Low: {info['low']:.2f}")
        print(f"Range Change: {info['change']:.2f}")
        print(f"Range Change (%): {info['change_percent']:.2f}%")
        print("-" * 20)

def plot_price(data, ticker, time_range):
    import plotext as plt

    close_prices = data['Close'].dropna()
    if close_prices.empty:
        print(f"No closing-price data available for {ticker}")
        return

    x_values = list(range(len(close_prices)))
    tick_count = min(5, len(close_prices))
    tick_positions = sorted({
        round(index * (len(close_prices) - 1) / (tick_count - 1))
        for index in range(tick_count)
    }) if tick_count > 1 else [0]
    tick_labels = [
        close_prices.index[position].strftime(
            TIME_RANGES[time_range]["date_format"]
        )
        for position in tick_positions
    ]

    plt.clear_figure()
    plt.plot_size(60, 15)
    plt.theme("clear")
    plt.plot(x_values, close_prices.tolist(), marker="braille")
    plt.xticks(tick_positions, tick_labels)
    period_high = data['High'].max()
    period_low = data['Low'].min()
    plt.title(
        f"{ticker} ({time_range}) | PTH {period_high:.2f} | PTL {period_low:.2f}"
    )
    plt.xlabel("Time" if time_range == "1d" else "Date")
    plt.ylabel("Price")
    plt.show()

def formatar(ativo):
    ativo = ativo.strip().upper()
    if "-" in ativo:
        return ativo
    if ativo.endswith(".SA"):
        return ativo
    return f"{ativo}.SA"

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
    ativo = formatar(ativo)
    print_info(get_info(ativo, args.time), mode)
    exit(0)

# Plot
if args.plot is True:
    ativo = input("Enter stock to generate the plot: ")
elif args.plot:
    ativo = args.plot
if ativo:
    ativo = formatar(ativo)
    info = get_info(ativo, args.time)
    if info:
        plot_price(info['raw_data'], ativo, args.time)
    exit(0)
for ativo in ativos:
    print_info(get_info(ativo, args.time), mode)
