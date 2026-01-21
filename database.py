import sqlite3
import json
from datetime import datetime
from engine import FinanceProfile, IncomeSource, Expense, BudgetStrategy

class DatabaseManager:
    def __init__(self, db_path: str = "finflow.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Profile settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profile_settings (
                    id INTEGER PRIMARY KEY,
                    balance REAL,
                    savings_goal REAL,
                    target_strategy TEXT
                )
            """)
            # Income sources table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS income_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    amount REAL,
                    pay_days TEXT
                )
            """)
            # Expenses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    amount REAL,
                    due_day INTEGER,
                    category TEXT,
                    priority INTEGER,
                    is_debt BOOLEAN
                )
            """)
            # Check if profile exists, if not create default
            cursor.execute("SELECT COUNT(*) FROM profile_settings")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO profile_settings (balance, savings_goal, target_strategy) VALUES (?, ?, ?)",
                               (0.0, 0.0, "Balanced"))
            conn.commit()

    def load_profile(self) -> FinanceProfile:
        profile = FinanceProfile()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Load settings
            cursor.execute("SELECT balance, savings_goal, target_strategy FROM profile_settings WHERE id = 1")
            row = cursor.fetchone()
            if row:
                profile.balance = row[0]
                profile.savings_goal = row[1]
                profile.target_strategy = BudgetStrategy(row[2])

            # Load income sources
            cursor.execute("SELECT name, amount, pay_days FROM income_sources")
            for name, amount, pay_days_str in cursor.fetchall():
                pay_days = [int(d) for d in pay_days_str.split(',')]
                profile.income_sources.append(IncomeSource(name, amount, pay_days))

            # Load expenses
            cursor.execute("SELECT name, amount, due_day, category, priority, is_debt FROM expenses")
            for name, amount, due_day, category, priority, is_debt in cursor.fetchall():
                profile.expenses.append(Expense(name, amount, due_day, category, priority, bool(is_debt)))

        return profile

    def save_profile(self, profile: FinanceProfile):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Save settings
            cursor.execute("""
                UPDATE profile_settings 
                SET balance = ?, savings_goal = ?, target_strategy = ?
                WHERE id = 1
            """, (profile.balance, profile.savings_goal, profile.target_strategy.value))

            # Save income (simple approach: clear and re-insert)
            cursor.execute("DELETE FROM income_sources")
            for source in profile.income_sources:
                cursor.execute("INSERT INTO income_sources (name, amount, pay_days) VALUES (?, ?, ?)",
                               (source.name, source.amount, ",".join(map(str, source.pay_days))))

            # Save expenses
            cursor.execute("DELETE FROM expenses")
            for exp in profile.expenses:
                cursor.execute("""
                    INSERT INTO expenses (name, amount, due_day, category, priority, is_debt)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (exp.name, exp.amount, exp.due_day, exp.category, exp.priority, exp.is_debt))
            
            conn.commit()
