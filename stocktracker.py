#!/usr/bin/env python3
"""An interactive terminal dashboard for Yahoo Finance quotes."""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from datetime import datetime
from threading import Thread
from typing import Sequence

from rich.console import Group
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Footer, Header, Input, ListItem, ListView, Static


@dataclass(frozen=True)
class TimeRange:
    """Yahoo Finance parameters and UI copy for a selectable period."""

    period: str
    interval: str
    label: str
    description: str


TIME_RANGES: dict[str, TimeRange] = {
    "1d": TimeRange("1d", "1m", "1D", "Today"),
    "1w": TimeRange("7d", "30m", "1W", "Past week"),
    "1m": TimeRange("1mo", "1d", "1M", "Past month"),
    "1y": TimeRange("1y", "1wk", "1Y", "Past year"),
}
PERIOD_KEYS = tuple(TIME_RANGES)
DEFAULT_TICKERS = ("PETR4.SA", "BBAS3.SA", "BTC-USD")
BRAZILIAN_TICKER = re.compile(r"^[A-Z]{4}\d{1,2}$")
VALID_TICKER = re.compile(r"^[A-Z0-9^][A-Z0-9.^=_-]{0,19}$")
BLOCKS = " ▁▂▃▄▅▆▇█"


@dataclass(frozen=True)
class StockSnapshot:
    """UI-friendly stock data detached from yfinance/pandas objects."""

    ticker: str
    period: str
    current: float
    start: float
    high: float
    low: float
    change: float
    change_percent: float
    prices: tuple[float, ...]
    fetched_at: datetime


class SnapshotLoaded(Message):
    """Thread-safe handoff from the quote worker to the UI."""

    def __init__(
        self,
        ticker: str,
        period: str,
        generation: int,
        snapshot: StockSnapshot | None,
        error: str | None,
    ) -> None:
        super().__init__()
        self.ticker = ticker
        self.period = period
        self.generation = generation
        self.snapshot = snapshot
        self.error = error


def normalize_ticker(value: str) -> str:
    """Normalize a search term to a Yahoo Finance ticker."""

    ticker = value.strip().upper()
    if not ticker:
        raise ValueError("Enter a ticker symbol.")
    if not VALID_TICKER.fullmatch(ticker):
        raise ValueError("Use letters, numbers, '.', '-', '^', '=' or '_'.")
    if BRAZILIAN_TICKER.fullmatch(ticker):
        return f"{ticker}.SA"
    return ticker


def short_ticker(ticker: str) -> str:
    """Return a compact display name without changing the Yahoo symbol."""

    return ticker.removesuffix(".SA")


def market_name(ticker: str) -> str:
    if ticker.endswith(".SA"):
        return "B3 · Brazil"
    if ticker.endswith("-USD"):
        return "Crypto · USD"
    if ticker.startswith("^"):
        return "Market index"
    return "Yahoo Finance"


def format_price(ticker: str, value: float) -> str:
    """Format a quote with a useful currency hint and precision."""

    if ticker.endswith(".SA"):
        prefix = "R$ "
    elif ticker.endswith("-USD") or "." not in ticker:
        prefix = "$"
    else:
        prefix = ""
    precision = 4 if 0 < abs(value) < 1 else 2
    return f"{prefix}{value:,.{precision}f}"


def sample_series(values: Sequence[float], width: int) -> tuple[float, ...]:
    """Sample a series across its complete extent to fit a terminal width."""

    if width <= 0 or not values:
        return ()
    if width == 1:
        return (float(values[-1]),)
    if len(values) <= width:
        return tuple(float(value) for value in values)
    last = len(values) - 1
    return tuple(float(values[round(column * last / (width - 1))]) for column in range(width))


def render_area_chart(
    values: Sequence[float], width: int, height: int
) -> tuple[str, ...]:
    """Render a compact, filled chart using one-eighth Unicode blocks."""

    sampled = sample_series(values, width)
    if not sampled or height <= 0:
        return ()

    floor = min(sampled)
    ceiling = max(sampled)
    span = ceiling - floor
    cells = height * 8
    if math.isclose(span, 0.0):
        levels = [max(1, cells // 2)] * len(sampled)
    else:
        levels = [
            1 + round(((value - floor) / span) * (cells - 1))
            for value in sampled
        ]

    rows: list[str] = []
    for row in reversed(range(height)):
        row_floor = row * 8
        rows.append(
            "".join(BLOCKS[min(8, max(0, level - row_floor))] for level in levels)
        )
    return tuple(rows)


class StockService:
    """Fetch and translate Yahoo Finance data."""

    def fetch(self, ticker: str, period: str) -> StockSnapshot:
        # Delayed import makes argument parsing and pure helper tests inexpensive.
        import yfinance as yf

        options = TIME_RANGES[period]
        data = yf.Ticker(ticker).history(
            period=options.period,
            interval=options.interval,
            timeout=10,
        )
        if data.empty:
            raise LookupError(f"No market data was returned for {ticker}.")

        missing_columns = {"Open", "High", "Low", "Close"} - set(data.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise LookupError(f"Yahoo Finance omitted required fields: {missing}.")

        closes = tuple(
            float(value)
            for value in data["Close"].dropna().tolist()
            if math.isfinite(float(value))
        )
        opens = tuple(
            float(value)
            for value in data["Open"].dropna().tolist()
            if math.isfinite(float(value))
        )
        highs = tuple(
            float(value)
            for value in data["High"].dropna().tolist()
            if math.isfinite(float(value))
        )
        lows = tuple(
            float(value)
            for value in data["Low"].dropna().tolist()
            if math.isfinite(float(value))
        )
        if not closes or not opens or not highs or not lows:
            raise LookupError(f"{ticker} has incomplete price history.")

        current = closes[-1]
        start = opens[0]
        change = current - start
        change_percent = (change / start * 100) if start else 0.0
        return StockSnapshot(
            ticker=ticker,
            period=period,
            current=current,
            start=start,
            high=max(highs),
            low=min(lows),
            change=change,
            change_percent=change_percent,
            prices=closes,
            fetched_at=datetime.now().astimezone(),
        )


class TickerListItem(ListItem):
    """A watchlist entry that retains its underlying Yahoo symbol."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        label = Text()
        label.append(short_ticker(ticker), style="bold")
        label.append(f"\n{market_name(ticker)}", style="dim")
        super().__init__(Static(label))


class PriceChart(Static):
    """Responsive terminal-native price area chart."""

    snapshot: StockSnapshot | None = None
    loading = False

    def show_snapshot(self, snapshot: StockSnapshot) -> None:
        self.snapshot = snapshot
        self.loading = False
        self.refresh()

    def show_loading(self) -> None:
        self.snapshot = None
        self.loading = True
        self.refresh()

    def render(self) -> Group | Text:
        if self.loading:
            return Text("Loading price history…", style="italic dim")
        if self.snapshot is None:
            return Text(
                "Price history is unavailable.",
                style="italic dim",
            )

        snapshot = self.snapshot
        width = max(4, self.size.width - 4)
        height = max(2, self.size.height - 5)
        chart_rows = render_area_chart(snapshot.prices, width, height)
        color = "green" if snapshot.change >= 0 else "red"

        scale = Text(no_wrap=True, overflow="crop")
        scale.append(
            f"HIGH  {format_price(snapshot.ticker, snapshot.high)}",
            style="bold dim",
        )
        scale.append(" " * 4)
        scale.append(
            f"LOW  {format_price(snapshot.ticker, snapshot.low)}",
            style="bold dim",
        )
        lines: list[Text] = [scale]
        lines.extend(Text(row, style=color, no_wrap=True, overflow="crop") for row in chart_rows)

        caption = Text(no_wrap=True, overflow="crop")
        caption.append(
            TIME_RANGES[snapshot.period].description,
            style="dim",
        )
        caption.append("  ·  ")
        caption.append(
            f"{len(snapshot.prices):,} points",
            style="dim",
        )
        lines.append(caption)
        return Group(*lines)


class StockTrackerApp(App[None]):
    """Mouse- and keyboard-driven stock tracker."""

    TITLE = "StockTracker"
    SUB_TITLE = "Yahoo Finance terminal dashboard"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "reload", "Reload"),
        Binding("j", "next_ticker", "Next"),
        Binding("k", "previous_ticker", "Previous"),
        Binding("h", "previous_period", "Earlier range"),
        Binding("l", "next_period", "Later range"),
        Binding("/", "focus_search", "Search"),
        Binding("escape", "cancel_search", "Back", show=False),
    ]

    CSS = """
    Screen {
        background: ansi_default;
        color: ansi_default;
    }

    Header {
        background: ansi_default;
        color: ansi_default;
    }

    HeaderIcon:hover {
        background: ansi_default;
        text-style: reverse;
    }

    Footer {
        background: ansi_default;
        color: ansi_default;
    }

    FooterKey {
        background: ansi_default;
        color: ansi_default;

        .footer-key--key {
            background: ansi_default;
            color: ansi_cyan;
        }

        .footer-key--description {
            background: ansi_default;
            color: ansi_default;
        }

        &:hover {
            background: ansi_default;
            color: ansi_default;
            text-style: reverse;
        }
    }

    #shell {
        height: 1fr;
    }

    #toolbar {
        height: 5;
        padding: 1 2;
        background: ansi_default;
        border-bottom: solid ansi_bright_black;
    }

    #brand {
        width: 20;
        height: 3;
        content-align: left middle;
        color: ansi_cyan;
        text-style: bold;
    }

    #search {
        width: 1fr;
        max-width: 46;
        height: 3;
        margin-right: 2;
        border: tall ansi_bright_black;
        background: ansi_default;
        color: ansi_default;
    }

    #search:focus {
        border: tall ansi_cyan;
    }

    .period-button {
        width: 7;
        min-width: 5;
        height: 3;
        margin-right: 1;
        background: ansi_default;
        color: ansi_default;
        border: tall ansi_bright_black;
    }

    .period-button.active-period {
        background: ansi_default;
        color: ansi_default;
        border: tall ansi_cyan;
        text-style: bold reverse;
    }

    #refresh-button {
        width: 12;
        min-width: 10;
        height: 3;
        background: ansi_default;
        color: ansi_cyan;
        border: tall ansi_cyan;
    }

    #content {
        height: 1fr;
    }

    #sidebar {
        width: 27;
        min-width: 21;
        background: ansi_default;
        border-right: solid ansi_bright_black;
    }

    #watchlist-title {
        height: 3;
        padding: 1 2 0 2;
        color: ansi_default;
        text-style: bold;
    }

    #ticker-list {
        height: 1fr;
        padding: 0 1;
        background: ansi_default;
        scrollbar-color: ansi_bright_black;
        scrollbar-background: ansi_default;
    }

    TickerListItem {
        height: 4;
        padding: 1 1;
        margin-bottom: 1;
        color: ansi_default;
        background: ansi_default;
        border-left: thick transparent;
    }

    TickerListItem:hover {
        background: ansi_default;
        border-left: thick ansi_bright_black;
        text-style: underline;
    }

    TickerListItem.-highlight {
        background: ansi_default;
        color: ansi_default;
        border-left: thick ansi_cyan;
        text-style: bold reverse;
    }

    #watchlist-help {
        height: 4;
        padding: 1 2;
        color: ansi_default;
        text-opacity: 55%;
    }

    #dashboard {
        width: 1fr;
        height: 1fr;
        padding: 1 2 2 2;
        scrollbar-color: ansi_bright_black;
        scrollbar-background: ansi_default;
    }

    #status {
        height: 2;
        color: ansi_default;
        text-opacity: 65%;
    }

    #summary {
        height: 7;
        margin-bottom: 1;
        background: ansi_default;
        border: solid ansi_bright_black;
    }

    #identity {
        width: 1fr;
        padding: 1 2;
        content-align: left middle;
    }

    #quote {
        width: 1fr;
        padding: 1 2;
        content-align: right middle;
        text-align: right;
    }

    #metrics {
        height: 7;
        margin-bottom: 1;
    }

    .metric-card {
        width: 1fr;
        height: 7;
        margin-right: 1;
        padding: 1 2;
        background: ansi_default;
        border: solid ansi_bright_black;
        content-align: left middle;
    }

    #metric-low {
        margin-right: 0;
    }

    PriceChart {
        height: 1fr;
        min-height: 12;
        padding: 1 2;
        background: ansi_default;
        border: solid ansi_bright_black;
    }
    """

    def __init__(
        self,
        tickers: Sequence[str] = DEFAULT_TICKERS,
        period: str = "1d",
        service: StockService | None = None,
    ) -> None:
        # Preserve the user's terminal-defined ANSI palette instead of
        # converting ANSI colors to Textual's built-in truecolor theme.
        super().__init__(ansi_color=True)
        if period not in TIME_RANGES:
            raise ValueError(f"Unknown period: {period}")
        normalized = list(dict.fromkeys(normalize_ticker(ticker) for ticker in tickers))
        if not normalized:
            normalized = list(DEFAULT_TICKERS)
        self.portfolio = normalized
        self.current_ticker = normalized[0]
        self.current_period = period
        self.service = service or StockService()
        self.cache: dict[tuple[str, str], StockSnapshot] = {}
        self._load_generation = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="shell"):
            with Horizontal(id="toolbar"):
                yield Static("◈  STOCKTRACKER", id="brand")
                yield Input(
                    placeholder="/  Search ticker (PETR4, AAPL, BTC-USD)",
                    id="search",
                    max_length=20,
                )
                for key, options in TIME_RANGES.items():
                    classes = "period-button active-period" if key == self.current_period else "period-button"
                    yield Button(options.label, id=f"period-{key}", classes=classes, flat=True)
                yield Button("Reload", id="refresh-button", flat=True)
            with Horizontal(id="content"):
                with Vertical(id="sidebar"):
                    yield Static("WATCHLIST", id="watchlist-title")
                    yield ListView(
                        *(TickerListItem(ticker) for ticker in self.portfolio),
                        id="ticker-list",
                        initial_index=0,
                    )
                    yield Static("Click a ticker\nor use j / k", id="watchlist-help")
                with VerticalScroll(id="dashboard"):
                    yield Static("", id="status")
                    with Horizontal(id="summary"):
                        yield Static("", id="identity")
                        yield Static("", id="quote")
                    with Horizontal(id="metrics"):
                        yield Static("", id="metric-open", classes="metric-card")
                        yield Static("", id="metric-high", classes="metric-card")
                        yield Static("", id="metric-low", classes="metric-card")
                    yield PriceChart(id="price-chart")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#ticker-list", ListView).focus()
        self._sync_period_buttons()
        self.request_snapshot()

    def _metric(self, label: str, value: str) -> Text:
        text = Text()
        text.append(label.upper(), style="bold dim")
        text.append(f"\n{value}", style="bold")
        return text

    def _render_snapshot(self, snapshot: StockSnapshot) -> None:
        identity = Text()
        identity.append(
            short_ticker(snapshot.ticker),
            style="bold",
        )
        identity.append(
            f"\n{snapshot.ticker}  ·  {market_name(snapshot.ticker)}",
            style="dim",
        )
        self.query_one("#identity", Static).update(identity)

        direction = "+" if snapshot.change >= 0 else ""
        color = "green" if snapshot.change >= 0 else "red"
        quote = Text(justify="right")
        quote.append(
            format_price(snapshot.ticker, snapshot.current),
            style="bold",
        )
        quote.append(
            f"\n{direction}{snapshot.change:,.2f}  "
            f"({direction}{snapshot.change_percent:.2f}%)",
            style=f"bold {color}",
        )
        self.query_one("#quote", Static).update(quote)
        self.query_one("#metric-open", Static).update(
            self._metric("Period open", format_price(snapshot.ticker, snapshot.start))
        )
        self.query_one("#metric-high", Static).update(
            self._metric("Period high", format_price(snapshot.ticker, snapshot.high))
        )
        self.query_one("#metric-low", Static).update(
            self._metric("Period low", format_price(snapshot.ticker, snapshot.low))
        )
        self.query_one("#price-chart", PriceChart).show_snapshot(snapshot)

    def _render_loading_shell(self) -> None:
        ticker = self.current_ticker
        identity = Text()
        identity.append(short_ticker(ticker), style="bold")
        identity.append(
            f"\n{ticker}  ·  {market_name(ticker)}",
            style="dim",
        )
        self.query_one("#identity", Static).update(identity)
        self.query_one("#quote", Static).update(
            Text(
                "—\nLoading…",
                justify="right",
                style="dim",
            )
        )
        for widget_id, label in (
            ("#metric-open", "Period open"),
            ("#metric-high", "Period high"),
            ("#metric-low", "Period low"),
        ):
            self.query_one(widget_id, Static).update(self._metric(label, "—"))
        self.query_one("#price-chart", PriceChart).show_loading()

    def _set_status(self, message: str, *, error: bool = False) -> None:
        style = "bold red" if error else "dim"
        self.query_one("#status", Static).update(Text(message, style=style))

    def _sync_period_buttons(self) -> None:
        for key in PERIOD_KEYS:
            button = self.query_one(f"#period-{key}", Button)
            button.set_class(key == self.current_period, "active-period")

    def activate_ticker(self, ticker: str) -> None:
        if ticker == self.current_ticker:
            return
        self.current_ticker = ticker
        self.request_snapshot()

    def request_snapshot(self, *, force: bool = False) -> None:
        key = (self.current_ticker, self.current_period)
        cached = self.cache.get(key)
        if cached is not None:
            self._render_snapshot(cached)
            if not force:
                self._set_status(
                    f"{TIME_RANGES[self.current_period].label} view  ·  "
                    f"cached at {cached.fetched_at:%H:%M:%S}  ·  press r to refresh"
                )
                return
            self._set_status(f"Refreshing {self.current_ticker}…")
        else:
            self._render_loading_shell()
            self._set_status(
                f"Loading {self.current_ticker} · {TIME_RANGES[self.current_period].label}…"
            )

        self._load_generation += 1
        thread = Thread(
            target=self.load_snapshot,
            args=(
                self.current_ticker,
                self.current_period,
                self._load_generation,
            ),
            name=f"quote-{self._load_generation}",
            daemon=True,
        )
        thread.start()

    def load_snapshot(self, ticker: str, period: str, generation: int) -> None:
        """Fetch without blocking Textual's event loop."""

        try:
            snapshot = self.service.fetch(ticker, period)
        except Exception as error:
            self.post_message(
                SnapshotLoaded(ticker, period, generation, None, str(error))
            )
        else:
            self.post_message(
                SnapshotLoaded(ticker, period, generation, snapshot, None)
            )

    def on_snapshot_loaded(self, event: SnapshotLoaded) -> None:
        if event.generation != self._load_generation:
            return
        if (event.ticker, event.period) != (
            self.current_ticker,
            self.current_period,
        ):
            return
        if event.error is not None or event.snapshot is None:
            self.query_one("#price-chart", PriceChart).loading = False
            self.query_one("#price-chart", PriceChart).refresh()
            self._set_status(
                event.error or f"Unable to load {event.ticker}.",
                error=True,
            )
            return

        snapshot = event.snapshot
        self.cache[(event.ticker, event.period)] = snapshot
        self._render_snapshot(snapshot)
        self._set_status(
            f"{TIME_RANGES[event.period].label} view  ·  "
            f"updated {snapshot.fetched_at:%H:%M:%S}"
        )

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if isinstance(event.item, TickerListItem):
            self.activate_ticker(event.item.ticker)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, TickerListItem):
            self.activate_ticker(event.item.ticker)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        try:
            ticker = normalize_ticker(event.value)
        except ValueError as error:
            self._set_status(str(error), error=True)
            self.notify(str(error), severity="error")
            return

        if ticker not in self.portfolio:
            self.portfolio.append(ticker)
            await self.query_one("#ticker-list", ListView).append(TickerListItem(ticker))
        index = self.portfolio.index(ticker)
        ticker_list = self.query_one("#ticker-list", ListView)
        self.current_ticker = ticker
        ticker_list.index = index
        ticker_list.focus()
        event.input.value = ""
        self.request_snapshot()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "refresh-button":
            self.request_snapshot(force=True)
            return
        if button_id.startswith("period-"):
            self.select_period(button_id.removeprefix("period-"))

    def select_period(self, period: str) -> None:
        if period not in TIME_RANGES or period == self.current_period:
            return
        self.current_period = period
        self._sync_period_buttons()
        self.request_snapshot()

    def _move_ticker(self, amount: int) -> None:
        index = self.portfolio.index(self.current_ticker)
        index = (index + amount) % len(self.portfolio)
        ticker_list = self.query_one("#ticker-list", ListView)
        ticker_list.index = index
        ticker_list.focus()
        self.activate_ticker(self.portfolio[index])

    def _move_period(self, amount: int) -> None:
        index = PERIOD_KEYS.index(self.current_period)
        self.select_period(PERIOD_KEYS[(index + amount) % len(PERIOD_KEYS)])

    def action_reload(self) -> None:
        self.request_snapshot(force=True)

    def action_next_ticker(self) -> None:
        self._move_ticker(1)

    def action_previous_ticker(self) -> None:
        self._move_ticker(-1)

    def action_previous_period(self) -> None:
        self._move_period(-1)

    def action_next_period(self) -> None:
        self._move_period(1)

    def action_focus_search(self) -> None:
        search = self.query_one("#search", Input)
        search.value = ""
        search.focus()

    def action_cancel_search(self) -> None:
        self.query_one("#search", Input).value = ""
        self.query_one("#ticker-list", ListView).focus()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open an interactive terminal stock dashboard.",
    )
    parser.add_argument(
        "tickers",
        nargs="*",
        metavar="TICKER",
        help="initial watchlist (default: PETR4.SA BBAS3.SA BTC-USD)",
    )
    parser.add_argument(
        "-t",
        "--time",
        choices=TIME_RANGES,
        default="1d",
        help="initial chart period (default: 1d)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    tickers = args.tickers or DEFAULT_TICKERS
    try:
        app = StockTrackerApp(tickers=tickers, period=args.time)
    except ValueError as error:
        raise SystemExit(f"stocktracker: {error}") from error
    app.run()


if __name__ == "__main__":
    main()
