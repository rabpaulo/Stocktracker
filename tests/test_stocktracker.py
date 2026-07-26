from __future__ import annotations

import unittest
from datetime import datetime

from stocktracker import (
    StockSnapshot,
    StockTrackerApp,
    format_price,
    normalize_ticker,
    render_area_chart,
    sample_series,
)


class HelperTests(unittest.TestCase):
    def test_normalizes_brazilian_and_yahoo_tickers(self) -> None:
        self.assertEqual(normalize_ticker(" petr4 "), "PETR4.SA")
        self.assertEqual(normalize_ticker("bova11"), "BOVA11.SA")
        self.assertEqual(normalize_ticker("aapl"), "AAPL")
        self.assertEqual(normalize_ticker("btc-usd"), "BTC-USD")
        self.assertEqual(normalize_ticker("^bvsp"), "^BVSP")

    def test_rejects_empty_or_unsafe_tickers(self) -> None:
        with self.assertRaisesRegex(ValueError, "Enter a ticker"):
            normalize_ticker(" ")
        with self.assertRaisesRegex(ValueError, "letters"):
            normalize_ticker("PETR4[]")

    def test_formats_currency_and_small_values(self) -> None:
        self.assertEqual(format_price("PETR4.SA", 42.5), "R$ 42.50")
        self.assertEqual(format_price("AAPL", 212.123), "$212.12")
        self.assertEqual(format_price("BTC-USD", 0.123456), "$0.1235")

    def test_samples_the_full_series(self) -> None:
        values = tuple(float(value) for value in range(100))
        self.assertEqual(sample_series(values, 3), (0.0, 50.0, 99.0))
        self.assertEqual(sample_series(values, 1), (99.0,))
        self.assertEqual(sample_series(values, 0), ())

    def test_area_chart_has_requested_dimensions(self) -> None:
        chart = render_area_chart((10, 15, 12, 20), width=4, height=3)
        self.assertEqual(len(chart), 3)
        self.assertTrue(all(len(row) == 4 for row in chart))
        self.assertIn("█", "".join(chart))

    def test_flat_area_chart_still_renders(self) -> None:
        chart = render_area_chart((10, 10, 10), width=3, height=2)
        self.assertEqual(len(chart), 2)
        self.assertNotEqual("".join(chart).strip(), "")


class FakeStockService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def fetch(self, ticker: str, period: str) -> StockSnapshot:
        self.calls.append((ticker, period))
        offset = float(len(self.calls))
        return StockSnapshot(
            ticker=ticker,
            period=period,
            current=102.0 + offset,
            start=100.0,
            high=104.0 + offset,
            low=98.0,
            change=2.0 + offset,
            change_percent=2.0 + offset,
            prices=(100.0, 101.0, 99.0, 102.0 + offset),
            fetched_at=datetime.now().astimezone(),
        )


class AppInteractionTests(unittest.IsolatedAsyncioTestCase):
    async def settle(self, pilot, turns: int = 5) -> None:
        for _ in range(turns):
            await pilot.pause(0.01)

    async def test_keyboard_search_period_navigation_and_reload(self) -> None:
        service = FakeStockService()
        app = StockTrackerApp(service=service)

        async with app.run_test(size=(120, 40)) as pilot:
            await self.settle(pilot)
            self.assertEqual(app.current_ticker, "PETR4.SA")

            await pilot.press("j")
            await self.settle(pilot)
            self.assertEqual(app.current_ticker, "BBAS3.SA")

            await pilot.press("l")
            await self.settle(pilot)
            self.assertEqual(app.current_period, "1w")

            await pilot.press("/")
            # A symbol containing j verifies watchlist bindings don't steal
            # printable characters while the search input is focused.
            await pilot.press("j", "n", "j", "enter")
            await self.settle(pilot)
            self.assertEqual(app.current_ticker, "JNJ")
            self.assertIn("JNJ", app.portfolio)

            calls_before_reload = len(service.calls)
            await pilot.press("r")
            await self.settle(pilot)
            self.assertGreater(len(service.calls), calls_before_reload)

    async def test_mouse_period_and_refresh_controls(self) -> None:
        service = FakeStockService()
        app = StockTrackerApp(service=service)

        async with app.run_test(size=(120, 40)) as pilot:
            await self.settle(pilot)
            second_ticker = app.query_one("#ticker-list").children[1]
            await pilot.click(second_ticker, offset=(1, 1))
            await self.settle(pilot)
            self.assertEqual(app.current_ticker, "BBAS3.SA")

            await pilot.click("#period-1m")
            await self.settle(pilot)
            self.assertEqual(app.current_period, "1m")

            calls_before_reload = len(service.calls)
            await pilot.click("#refresh-button")
            await self.settle(pilot)
            self.assertGreater(len(service.calls), calls_before_reload)


if __name__ == "__main__":
    unittest.main()
