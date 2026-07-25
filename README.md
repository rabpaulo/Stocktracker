# StockTracker

Simple Python CLI for tracking stocks and cryptocurrencies with data from Yahoo
Finance.

## Features

- Display a detailed or compact portfolio summary.
- Search for a specific ticker.
- Render a compact price chart directly in the terminal.
- Use the terminal's default foreground and background colors.
- Select data ranges of one day, week, month, or year.
- Display the Period Time High (PTH) and Period Time Low (PTL) in the chart
  title.

## Installation

```bash
git clone https://github.com/rabpaulo/Stocktracker
cd Stocktracker
python3 -m pip install -r requirements.txt
```

## Usage

```text
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

Display the default portfolio:

```bash
./stocktracker.py
```

Display only current prices:

```bash
./stocktracker.py --simple
```

Find a specific asset:

```bash
./stocktracker.py --find PETR4
./stocktracker.py --find BTC-USD
```

Generate a compact terminal chart:

```bash
./stocktracker.py --plot PETR4
./stocktracker.py --plot PETR4 --time 1m
./stocktracker.py -p BTC-USD -t 1y
```

Brazilian stock tickers automatically receive the `.SA` suffix when omitted.
Tickers containing a hyphen, such as `BTC-USD`, are preserved.

## Time ranges

| Value | Range | Data interval |
| --- | --- | --- |
| `1d` | One day | One minute |
| `1w` | One week | Thirty minutes |
| `1m` | One month | One day |
| `1y` | One year | One week |

The default range is `1d`. In this CLI, `1m` means one month.

## Chart indicators

The chart title includes the selected ticker, range, and price extremes:

```text
PETR4.SA (1m) | PTH 42.10 | PTL 35.72
```

- **PTH (Period Time High):** highest `High` price in the selected range.
- **PTL (Period Time Low):** lowest `Low` price in the selected range.
