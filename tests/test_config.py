import errno
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from textual.widgets import Input

from main import ConfigError, ConfigStore, StockSnapshot, StockTrackerApp


class FakeStockService:
    def fetch(self, ticker: str, period: str) -> StockSnapshot:
        now = datetime.now().astimezone()
        return StockSnapshot(
            ticker=ticker,
            period=period,
            current=11,
            start=10,
            high=12,
            low=9,
            change=1,
            change_percent=10,
            prices=(10, 11),
            timestamps=(now, now),
            fetched_at=now,
        )


class ConfigStoreTests(unittest.TestCase):
    def make_config(
        self,
        directory: str,
        document: object,
    ) -> Path:
        path = Path(directory, "stocktracker.json")
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def test_load_tickers_normalizes_and_removes_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_config(
                directory,
                {"tickers": ["petr4", "PETR4.SA", " btc-usd "]},
            )

            tickers = ConfigStore(path).load_tickers()

            self.assertEqual(tickers, ("PETR4.SA", "BTC-USD"))

    def test_add_ticker_persists_normalized_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_config(
                directory,
                {"tickers": ["PETR4.SA"], "unrelated": "preserved"},
            )
            store = ConfigStore(path)

            changed = store.add_ticker("bova11")

            self.assertTrue(changed)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {
                    "tickers": ["PETR4.SA", "BOVA11.SA"],
                    "unrelated": "preserved",
                },
            )

    def test_add_ticker_does_not_duplicate_existing_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_config(directory, {"tickers": ["PETR4.SA"]})
            store = ConfigStore(path)

            changed = store.add_ticker("petr4")

            self.assertFalse(changed)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"tickers": ["PETR4.SA"]},
            )

    def test_add_ticker_supports_a_docker_bind_mounted_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_config(directory, {"tickers": ["PETR4.SA"]})
            store = ConfigStore(path)

            with patch.object(
                Path,
                "replace",
                side_effect=OSError(errno.EBUSY, "Device or resource busy"),
            ):
                changed = store.add_ticker("AAPL")

            self.assertTrue(changed)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"tickers": ["PETR4.SA", "AAPL"]},
            )

    def test_add_ticker_supports_a_non_writable_bind_mount_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_config(directory, {"tickers": ["PETR4.SA"]})
            store = ConfigStore(path)
            temporary_path = str(path.parent / f".{path.name}.temporary")

            with patch(
                "main.NamedTemporaryFile",
                side_effect=PermissionError(
                    errno.EACCES,
                    "Permission denied",
                    temporary_path,
                ),
            ):
                changed = store.add_ticker("AAPL")

            self.assertTrue(changed)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"tickers": ["PETR4.SA", "AAPL"]},
            )

    def test_empty_watchlist_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_config(directory, {"tickers": []})

            with self.assertRaisesRegex(ConfigError, "cannot be empty"):
                ConfigStore(path).load_tickers()

    def test_invalid_ticker_reports_its_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_config(directory, {"tickers": ["AAPL", "not valid!"]})

            with self.assertRaisesRegex(ConfigError, r'tickers\[1\]'):
                ConfigStore(path).load_tickers()


class WatchlistPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_input_accepts_lowercase_characters(self) -> None:
        app = StockTrackerApp(
            ("PETR4.SA",),
            service=FakeStockService(),
        )

        async with app.run_test() as pilot:
            await pilot.press("/")
            await pilot.press("p", "e", "t", "r", "4")

            self.assertEqual(app.query_one("#search", Input).value, "petr4")

    async def test_search_opens_ticker_without_saving_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "stocktracker.json")
            path.write_text('{"tickers": ["PETR4.SA"]}\n', encoding="utf-8")
            store = ConfigStore(path)
            app = StockTrackerApp(
                store.load_tickers(),
                service=FakeStockService(),
                config_store=store,
            )

            async with app.run_test() as pilot:
                await pilot.press("/")
                await pilot.press("a", "a", "p", "l", "enter")
                await pilot.pause()

            self.assertEqual(app.current_ticker, "AAPL")
            self.assertEqual(app.portfolio, ["PETR4.SA"])
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"tickers": ["PETR4.SA"]},
            )

    async def test_add_button_saves_ticker_to_watchlist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "stocktracker.json")
            path.write_text('{"tickers": ["PETR4.SA"]}\n', encoding="utf-8")
            store = ConfigStore(path)
            app = StockTrackerApp(
                store.load_tickers(),
                service=FakeStockService(),
                config_store=store,
            )

            async with app.run_test() as pilot:
                await pilot.press("/")
                await pilot.press("a", "a", "p", "l", "enter")
                await pilot.click("#add-button")
                await pilot.pause()

            self.assertEqual(app.current_ticker, "AAPL")
            self.assertEqual(app.portfolio, ["PETR4.SA", "AAPL"])
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"tickers": ["PETR4.SA", "AAPL"]},
            )

    async def test_add_footer_binding_saves_searched_ticker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "stocktracker.json")
            path.write_text('{"tickers": ["PETR4.SA"]}\n', encoding="utf-8")
            store = ConfigStore(path)
            app = StockTrackerApp(
                store.load_tickers(),
                service=FakeStockService(),
                config_store=store,
            )

            async with app.run_test() as pilot:
                await pilot.press("/")
                await pilot.press("m", "s", "f", "t", "enter")
                await pilot.press("a")
                await pilot.pause()

            self.assertEqual(app.current_ticker, "MSFT")
            self.assertEqual(app.portfolio, ["PETR4.SA", "MSFT"])
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"tickers": ["PETR4.SA", "MSFT"]},
            )


if __name__ == "__main__":
    unittest.main()
