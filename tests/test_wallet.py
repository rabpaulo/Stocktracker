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
    async def test_wallet_compares_average_cost_with_yahoo_price(self) -> None:
        entry = make_wallet_entry(
            "AAPL",
            "buy",
            2,
            10,
            datetime(2026, 7, 29, tzinfo=timezone.utc),
        )
        app = StockTrackerApp(
            ("AAPL",),
            service=FakeStockService(),
            wallet_entries=(entry,),
        )

        async with app.run_test() as pilot:
            await pilot.press("2")
            await pilot.pause()

            table = app.query_one("#wallet-positions-table", DataTable)
            row = table.get_row_at(0)

            self.assertEqual(row[0], "AAPL")
            self.assertEqual(row[1], "2")
            self.assertEqual(row[2], "10.00")
            self.assertEqual(row[3], "11.00")
            self.assertEqual(row[4].plain, "+2.00")
            self.assertEqual(row[5].plain, "+10.00%")

    async def test_wallet_uses_vim_keys_to_navigate_the_entry_log(self) -> None:
        entries = tuple(
            make_wallet_entry(
                ticker,
                "buy",
                quantity,
                price,
                datetime(2026, 7, 29, 12, minute, tzinfo=timezone.utc),
            )
            for minute, ticker, quantity, price in (
                (0, "AAPL", 1, 100),
                (1, "MSFT", 2, 200),
                (2, "PETR4", 3, 30),
            )
        )
        app = StockTrackerApp(
            ("PETR4.SA",),
            service=FakeStockService(),
            wallet_entries=entries,
        )

        async with app.run_test() as pilot:
            await pilot.press("2")
            table = app.query_one("#wallet-table", DataTable)

            self.assertIs(app.focused, table)
            self.assertEqual(table.cursor_coordinate.row, 0)

            await pilot.press("j")
            self.assertEqual(table.cursor_coordinate.row, 1)

            await pilot.press("shift+g")
            self.assertEqual(table.cursor_coordinate.row, 2)

            await pilot.press("g")
            self.assertEqual(table.cursor_coordinate.row, 0)

            await pilot.press("k")
            self.assertEqual(table.cursor_coordinate.row, 0)

    async def test_wallet_edit_mode_preserves_values_when_returning_to_log(
        self,
    ) -> None:
        app = StockTrackerApp(
            ("PETR4.SA",),
            service=FakeStockService(),
        )

        async with app.run_test() as pilot:
            await pilot.press("2", "i")
            ticker = app.query_one("#wallet-ticker", Input)
            table = app.query_one("#wallet-table", DataTable)

            self.assertIs(app.focused, ticker)
            ticker.value = "AAPL"
            await pilot.press("escape")

            self.assertIs(app.focused, table)
            self.assertEqual(ticker.value, "AAPL")

    async def test_enter_advances_through_the_wallet_form(self) -> None:
        app = StockTrackerApp(
            ("PETR4.SA",),
            service=FakeStockService(),
        )

        async with app.run_test() as pilot:
            await pilot.press("2", "i", "enter")
            side = app.query_one("#wallet-side", Select)

            self.assertIs(app.focused, side)

            await pilot.press("j", "enter")

            self.assertEqual(side.value, "sell")
            self.assertIs(
                app.focused,
                app.query_one("#wallet-quantity", Input),
            )

    async def test_enter_logs_an_entry_with_the_default_buy_side(self) -> None:
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
                await pilot.press("2", "i")
                await pilot.press(*"petr4", "enter", "enter")
                await pilot.press(*"10", "enter")
                await pilot.press(*"40.50", "enter")
                await pilot.pause()

                self.assertEqual(
                    app.query_one("#wallet-table", DataTable).row_count,
                    1,
                )

            saved = store.load_wallet_entries()
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].side, "buy")

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
