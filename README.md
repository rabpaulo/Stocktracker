# StockTracker

StockTracker is an interactive terminal dashboard for stocks, crypto, and market
indexes using data from Yahoo Finance. It is a full TUI: use the keyboard, click
controls with the mouse, or scroll the dashboard without leaving the terminal.

## Screenshots

Fresh captures from the running dashboard are stored in [`screenshots/`](screenshots/)
in both PNG and SVG formats.

### PETR4 · One day

![StockTracker showing PETR4 market data for one week](screenshots/petr41w.png)

### BTC-USD · One month

![StockTracker showing Bitcoin market data for one month](screenshots/BTC1m.png)

## What it shows

- A clickable watchlist
- Current price and period change
- Period open, high, and low
- A responsive terminal-native chart with price and date axes
- Cached views for instant navigation
- Background refreshes that do not freeze the interface
- Clear loading and data-provider error states
- Colors inherited from your terminal's active ANSI palette

## Installation

```bash
git clone https://github.com/rabpaulo/Stocktracker
cd Stocktracker
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Run

Open the default watchlist:

```bash
./stocktracker.py
```

Start with a custom watchlist or period:

```bash
./stocktracker.py AAPL MSFT BTC-USD
./stocktracker.py PETR4 BBAS3 -t 1m
```

Brazilian stock symbols such as `PETR4` and `BOVA11` automatically receive the
`.SA` suffix. Yahoo symbols that already contain a suffix or separator, such as
`BTC-USD`, `^BVSP`, and `VALE3.SA`, are preserved.

## Controls

| Input | Action |
| --- | --- |
| Mouse click | Select a ticker, period, search field, or reload button |
| Mouse wheel | Scroll the dashboard or watchlist |
| `j` / `k` | Select the next / previous ticker |
| `l` / `h` | Select the next / previous period |
| `/` | Focus ticker search |
| `Enter` | Open the ticker entered in search |
| `r` | Reload the selected ticker and period |
| `Esc` | Leave search and return to the watchlist |
| `q` | Quit |

The footer is also clickable in terminals with mouse reporting enabled.

## Periods

| Key | Range | Yahoo Finance interval |
| --- | --- | --- |
| `1d` | One trading day | One minute |
| `1w` | Seven days | Thirty minutes |
| `1m` | One month | One day |
| `1y` | One year | One week |
| `all` | All available history | One month |

In StockTracker, `1m` means one month.

## Notes

Quotes are supplied by Yahoo Finance through `yfinance` and may be delayed.
Previously loaded ticker/period combinations are cached for fast switching.
Press `r` or click **Reload** to request fresh data.

The interface uses your terminal's default foreground and background plus its
configured ANSI accent, success, and error colors. Changing your terminal color
scheme therefore changes StockTracker with it. When the `NO_COLOR` environment
variable is set, StockTracker renders in monochrome.
