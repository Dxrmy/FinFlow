from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, DataTable, Button, Input, TabbedContent, TabPane, Select
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from engine import FinanceEngine, FinanceProfile, IncomeSource, Expense, BudgetStrategy
from parser import StatementParser
from database import DatabaseManager
import pandas as pd
from datetime import datetime

class AddExpenseModal(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(classes="panel"):
            yield Static("Add New Expense", classes="stat-label")
            yield Input(placeholder="Name (e.g. Rent)", id="exp_name")
            yield Input(placeholder="Amount", id="exp_amount")
            yield Input(placeholder="Due Day (1-31)", id="exp_day")
            with Horizontal():
                yield Button("Cancel", id="cancel_btn")
                yield Button("Add", variant="primary", id="add_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add_btn":
            try:
                name = self.query_one("#exp_name", Input).value
                amount = float(self.query_one("#exp_amount", Input).value)
                day = int(self.query_one("#exp_day", Input).value)
                self.dismiss(Expense(name, amount, day, "Other", 1))
            except ValueError:
                self.dismiss(None)
        else:
            self.dismiss(None)

class AddIncomeModal(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(classes="panel"):
            yield Static("Add Income Source", classes="stat-label")
            yield Input(placeholder="Source Name (e.g. Job)", id="inc_name")
            yield Input(placeholder="Amount", id="inc_amount")
            yield Input(placeholder="Pay Days (comma separated, e.g. 15,28)", id="inc_days")
            with Horizontal():
                yield Button("Cancel", id="cancel_btn")
                yield Button("Add", variant="primary", id="add_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add_btn":
            try:
                name = self.query_one("#inc_name", Input).value
                amount = float(self.query_one("#inc_amount", Input).value)
                days_str = self.query_one("#inc_days", Input).value
                days = [int(d.strip()) for d in days_str.split(',')]
                self.dismiss(IncomeSource(name, amount, days))
            except ValueError:
                self.dismiss(None)
        else:
            self.dismiss(None)

class FinFlowApp(App):
    CSS = """
    Screen { background: #1a1a1a; }
    Header { background: #333; color: #fff; text-style: bold; }
    Footer { background: #333; }
    .panel { border: solid #444; padding: 1; margin: 1; height: auto; }
    #dashboard_grid { layout: grid; grid-size: 2; grid-gutter: 1; }
    .stat-label { color: #888; }
    .stat-value { text-style: bold; color: #00ff00; }
    Button { margin: 1; }
    """

    BINDINGS = [
        ("d", "switch_tab('dashboard_tab')", "Dashboard"),
        ("s", "switch_tab('statements_tab')", "Statements"),
        ("e", "switch_tab('expenses_tab')", "Expenses"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="tabs"):
            with TabPane("Dashboard", id="dashboard_tab"):
                with Horizontal():
                    with Vertical(classes="panel", id="stats_panel"):
                        yield Static("Balance: [b]£0.00[/b]", id="balance_display")
                        yield Static("Next Payday: [b]--[/b]", id="next_payday")
                        yield Static("Safe to Spend: [b]£0.00[/b]", id="safe_spend")
                        yield Static("Extra Debt Pay: [b]£0.00[/b]", id="extra_debt")
                    
                    with Vertical(classes="panel"):
                        yield Static("Strategy Selection", classes="stat-label")
                        yield Select(
                            [(s.value, s) for s in BudgetStrategy],
                            value=BudgetStrategy.BALANCED,
                            id="strategy_select"
                        )
                
                with Horizontal(id="dashboard_grid"):
                    with Vertical(classes="panel"):
                        yield Static("Upcoming Bills", classes="stat-label")
                        yield DataTable(id="upcoming_bills_table")
                    with Vertical(classes="panel"):
                        yield Static("Insights & Suggestions", classes="stat-label")
                        yield Static("Import a statement to see insights.", id="summary_tip")
            
            with TabPane("Statements", id="statements_tab"):
                yield Static("Import Bank Statement (CSV/PDF)", classes="panel")
                with Horizontal():
                    yield Input(placeholder="Absolute path to file...", id="path_input")
                    yield Button("Analyze", variant="primary", id="analyze_btn")
                yield DataTable(id="processed_data")
                yield Static("", id="analysis_text", classes="panel")
            
            with TabPane("Expenses", id="expenses_tab"):
                yield Static("Manage Finances", classes="panel")
                with Horizontal():
                    yield Button("Add Income Source", id="add_income_btn")
                    yield Button("Add Expense", id="add_expense_btn")
        yield Footer()

    def on_mount(self) -> None:
        self.db = DatabaseManager()
        self.profile = self.db.load_profile()
        self.engine = FinanceEngine(self.profile)
        self.parser = StatementParser()
        self.refresh_dashboard()

    def refresh_dashboard(self):
        self.db.save_profile(self.profile)
        analysis = self.engine.split_money(datetime.now())
        
        self.query_one("#balance_display", Static).update(f"Balance: [b]£{analysis['current_balance']:.2f}[/b]")
        self.query_one("#next_payday", Static).update(f"Next Payday: [b]{analysis['next_payday']}th[/b]")
        self.query_one("#safe_spend", Static).update(f"Safe to Spend: [b]£{analysis['safe_to_spend']:.2f}[/b]")
        self.query_one("#extra_debt", Static).update(f"Extra Debt Pay: [b]£{analysis['extra_debt_payment']:.2f}[/b]")
        
        table = self.query_one("#upcoming_bills_table", DataTable)
        table.clear()
        if not table.columns:
            table.add_columns("Name", "Due", "Amount")
        for bill in analysis['bills_upcoming']:
            table.add_row(bill['name'], f"{bill['due_day']}th", f"£{bill['amount']:.2f}")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "strategy_select":
            self.profile.target_strategy = event.value
            self.refresh_dashboard()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add_expense_btn":
            expense = await self.push_screen_wait(AddExpenseModal())
            if expense:
                self.profile.expenses.append(expense)
                self.refresh_dashboard()
        elif event.button.id == "add_income_btn":
            income = await self.push_screen_wait(AddIncomeModal())
            if income:
                self.profile.income_sources.append(income)
                self.refresh_dashboard()
        elif event.button.id == "analyze_btn":
            path = self.query_one("#path_input", Input).value
            if path:
                df = self.parser.parse_pdf(path) if path.lower().endswith('.pdf') else self.parser.parse_csv(path)
                if not df.empty:
                    self.update_statement_table(df)
                    insights = self.parser.get_spending_insights(df)
                    self.query_one("#analysis_text", Static).update(
                        f"Analysis Complete!\nTotal Spent: £{abs(insights.get('total_spent', 0)):.2f}\n"
                        f"Highest Expense: {insights.get('highest_category', 'N/A')}"
                    )
                    self.query_one("#summary_tip", Static).update(
                        f"Found high spending in: {insights.get('highest_category', 'N/A')}\n"
                        f"Switching to 'FIRE' or 'Aggressive' mode recommended."
                    )

    def update_statement_table(self, df: pd.DataFrame):
        table = self.query_one("#processed_data", DataTable)
        table.clear()
        if not table.columns:
            table.add_columns(*df.columns)
        for _, row in df.iterrows():
            table.add_row(*[str(val) for val in row])

if __name__ == "__main__":
    app = FinFlowApp()
    app.run()
