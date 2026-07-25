# StockTracker
Simple python script to track price of assets using the Yahoo Finance API.

## Requirements
yfinance
colorama
plotext

## Installation
```
git clone https://github.com/rabpaulo/Stocktracker
cd Stocktracker
pip install -r requirements.txt
```
# Usage
```
usage: stocktracker.py [-h] [-s] [-l] [-f [FIND]] [-p [PLOT]]
                       [-t {1d,1w,1m,1y}]

options:
  -h, --help            show this help message and exit
  -s, --simple          Simple printing mode
  -l, --list            List all stocks in the portfolio
  -f, --find [FIND]     Search for specific stock
  -p, --plot [PLOT]     Generate a CLI plot for the stock
  -t, --time {1d,1w,1m,1y}
                        Time range for stock data (default: 1d)
```

Generate an intraday price plot directly in the terminal:

```
./stocktracker.py --plot PETR4
```

Choose between one day, one week, one month, and one year:

```
./stocktracker.py --plot PETR4 --time 1m
```
