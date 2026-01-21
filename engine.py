import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Dict, Optional

from enum import Enum

class BudgetStrategy(Enum):
    BALANCED = "Balanced"
    AGGRESSIVE_DEBT = "Aggressive Debt"
    AGGRESSIVE_SAVINGS = "Aggressive Savings"
    SAFE_DEBT = "Safe Debt"
    SAFE_SAVINGS = "Safe Savings"
    FIRE = "FIRE (Extreme Frugality)"

@dataclass
class IncomeSource:
    name: str
    amount: float
    pay_days: List[int]
    recurring: bool = True

@dataclass
class Expense:
    name: str
    amount: float
    due_day: int
    category: str
    priority: int = 1
    is_debt: bool = False

@dataclass
class FinanceProfile:
    income_sources: List[IncomeSource] = field(default_factory=list)
    expenses: List[Expense] = field(default_factory=list)
    balance: float = 0.0
    savings_goal: float = 0.0
    target_strategy: BudgetStrategy = BudgetStrategy.BALANCED

    def to_json(self):
        data = asdict(self)
        data['target_strategy'] = self.target_strategy.value
        return json.dumps(data, indent=4)

    @classmethod
    def from_json(cls, data: str):
        obj = json.loads(data)
        profile = cls()
        profile.income_sources = [IncomeSource(**i) for i in obj.get('income_sources', [])]
        profile.expenses = [Expense(**e) for e in obj.get('expenses', [])]
        profile.balance = obj.get('balance', 0.0)
        profile.savings_goal = obj.get('savings_goal', 0.0)
        profile.target_strategy = BudgetStrategy(obj.get('target_strategy', "Balanced"))
        return profile

    def save_to_file(self, file_path: str = "profile.json"):
        with open(file_path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load_from_file(cls, file_path: str = "profile.json"):
        import os
        if not os.path.exists(file_path):
            return cls()
        with open(file_path, "r") as f:
            return cls.from_json(f.read())

class FinanceEngine:
    def __init__(self, profile: FinanceProfile):
        self.profile = profile

    def split_money(self, current_date: datetime):
        """
        Determines how to split the current balance based on upcoming bills,
        next paydays, and the selected strategy.
        """
        today = current_date.day
        current_month = current_date.month
        current_year = current_date.year

        # 1. Identify all upcoming paydays across all sources
        all_paydays = []
        for source in self.profile.income_sources:
            for day in source.pay_days:
                all_paydays.append(day)
        all_paydays = sorted(list(set(all_paydays)))

        # Find the NEXT payday
        next_payday = next((d for d in all_paydays if d > today), all_paydays[0] if all_paydays else today)
        
        # 2. Identify bills due before the NEXT payday
        bills_due = []
        critical_total = 0.0
        debt_total = 0.0
        
        for expense in self.profile.expenses:
            # Simple logic: if due_day > today and due_day <= next_payday (or if next_payday is earlier than today, meaning next month)
            is_upcoming = False
            if next_payday > today:
                if today < expense.due_day <= next_payday:
                    is_upcoming = True
            else: # Next payday is next month
                if expense.due_day > today or expense.due_day <= next_payday:
                    is_upcoming = True
            
            if is_upcoming:
                bills_due.append(expense)
                if expense.priority == 1:
                    critical_total += expense.amount
                if expense.is_debt:
                    debt_total += expense.amount

        # 3. Strategy-based logic
        strategy = self.profile.target_strategy
        safe_to_spend = self.profile.balance - critical_total
        
        extra_debt_payment = 0.0
        savings_contribution = 0.0

        if strategy == BudgetStrategy.AGGRESSIVE_DEBT:
            extra_debt_payment = max(0, safe_to_spend * 0.7)
            safe_to_spend -= extra_debt_payment
        elif strategy == BudgetStrategy.AGGRESSIVE_SAVINGS:
            savings_contribution = max(0, safe_to_spend * 0.7)
            safe_to_spend -= savings_contribution
        elif strategy == BudgetStrategy.FIRE:
            savings_contribution = max(0, safe_to_spend * 0.9)
            safe_to_spend -= savings_contribution
        elif strategy == BudgetStrategy.SAFE_DEBT:
            extra_debt_payment = max(0, safe_to_spend * 0.3)
            safe_to_spend -= extra_debt_payment
        elif strategy == BudgetStrategy.SAFE_SAVINGS:
            savings_contribution = max(0, safe_to_spend * 0.3)
            safe_to_spend -= savings_contribution
        
        # Buffer for 'Balanced'
        if strategy == BudgetStrategy.BALANCED:
            buffer = safe_to_spend * 0.2
            safe_to_spend -= buffer

        return {
            "current_balance": self.profile.balance,
            "next_payday": next_payday,
            "bills_upcoming": [asdict(b) for b in bills_due],
            "critical_total": critical_total,
            "extra_debt_payment": extra_debt_payment,
            "savings_contribution": savings_contribution,
            "safe_to_spend": max(0, safe_to_spend)
        }

    def analyze_spending(self, df_statement):
        """
        Analyze a pandas DataFrame of bank transactions.
        """
        # Basic example categorizer
        summary = df_statement.groupby('category')['amount'].sum().to_dict()
        suggestions = []
        
        # Identify recurring high-cost items
        # ... logic to follow
        
        return {
            "summary": summary,
            "suggestions": suggestions
        }
