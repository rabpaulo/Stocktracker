import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from textual.widgets import DataTable, Input, Select, TabbedContent

from main import (
    ConfigStore,
    StockTrackerApp,
    WalletEntry,
    calculate_wallet_positions,
    make_wallet_entry,
)
from tests.test_config import FakeStockService


class WalletCalculationTests(unittest.TestCase):
    def entry(
        self,
        ticker: str,
        side: str,
        quantity: float,
        price: float,
    ) -> WalletEntry:
        return make_wallet_entry(
            ticker,
            side,
            quantity,
            price,
            datetime(2026, 7, 29, tzinfo=timezone.utc),
        )

    def test_positions_use_weighted_average_cost_and_realized_profit(self) -> None:
        positions = calculate_wallet_positions(
            (
                self.entry("AAPL", "buy", 10, 100),
                self.entry("AAPL", "buy", 10, 200),
                self.entry("AAPL", "sell", 5, 180),
            )
        )

        self.assertEqual(len(positions), 1)
        position = positions[0]
        self.assertEqual(position.quantity, 15)
        self.assertEqual(position.average_cost, 150)
        self.assertEqual(position.cost_basis, 2250)
        self.assertEqual(position.realized_profit, 150)

    def test_position_calculation_rejects_an_oversell(self) -> None:
        with self.assertRaisesRegex(ValueError, "only 2 held"):
            calculate_wallet_positions(
                (
                    self.entry("AAPL", "buy", 2, 100),
                    self.entry("AAPL", "sell", 3, 120),
                )
            )


class WalletPersistenceTests(unittest.TestCase):
    def test_wallet_entries_round_trip_without_changing_other_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "stocktracker.json")
            path.write_text(
                json.dumps({"tickers": ["PETR4.SA"], "unrelated": "preserved"}),
                encoding="utf-8",
            )
            store = ConfigStore(path)
            entry = make_wallet_entry(
                "petr4",
                "buy",
                12.5,
                38.75,
                datetime(2026, 7, 29, 12, 30, tzinfo=timezone.utc),
            )

            store.add_wallet_entry(entry)

            self.assertEqual(store.load_wallet_entries(), (entry,))
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["unrelated"], "preserved")
            self.assertEqual(
                document["wallet_entries"],
                [
                    {
                        "ticker": "PETR4.SA",
                        "side": "buy",
                        "quantity": 12.5,
                        "price": 38.75,
                        "occurred_at": "2026-07-29T12:30:00+00:00",
                    }
                ],
            )


class WalletInterfaceTests(unittest.IsolatedAsyncioTestCase):
    async def test_wallet_tab_logs_and_renders_a_persistent_buy(self) -> None:
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
                await pilot.press("2")
                app.query_one("#wallet-ticker", Input).value = "petr4"
                app.query_one("#wallet-side", Select).value = "buy"
                app.query_one("#wallet-quantity", Input).value = "10"
                app.query_one("#wallet-price", Input).value = "40.50"
                await pilot.click("#wallet-entry-button")
                await pilot.pause()

                self.assertEqual(
                    app.query_one("#main-tabs", TabbedContent).active,
                    "wallet-tab",
                )
                self.assertEqual(app.query_one("#wallet-table", DataTable).row_count, 1)
                self.assertEqual(len(app.wallet_entries), 1)

            saved = store.load_wallet_entries()
            self.assertEqual(saved[0].ticker, "PETR4.SA")
            self.assertEqual(saved[0].side, "buy")
            self.assertEqual(saved[0].quantity, 10)
            self.assertEqual(saved[0].price, 40.5)

    async def test_wallet_rejects_a_sale_larger_than_the_position(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "stocktracker.json")
            path.write_text('{"tickers": ["AAPL"]}\n', encoding="utf-8")
            store = ConfigStore(path)
            buy = make_wallet_entry(
                "AAPL",
                "buy",
                2,
                100,
                datetime(2026, 7, 29, tzinfo=timezone.utc),
            )
            store.add_wallet_entry(buy)
            app = StockTrackerApp(
                store.load_tickers(),
                service=FakeStockService(),
                config_store=store,
                wallet_entries=store.load_wallet_entries(),
            )

            async with app.run_test() as pilot:
                await pilot.press("2")
                app.query_one("#wallet-ticker", Input).value = "AAPL"
                app.query_one("#wallet-side", Select).value = "sell"
                app.query_one("#wallet-quantity", Input).value = "3"
                app.query_one("#wallet-price", Input).value = "120"
                await pilot.click("#wallet-entry-button")
                await pilot.pause()

                self.assertEqual(len(app.wallet_entries), 1)
                self.assertEqual(
                    app.query_one("#wallet-table", DataTable).row_count,
                    1,
                )

            self.assertEqual(len(store.load_wallet_entries()), 1)


if __name__ == "__main__":
    unittest.main()
