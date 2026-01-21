import pandas as pd
import re
import pdfplumber
from typing import List, Dict

class StatementParser:
    def __init__(self):
        # ... categories stay the same ...
        # Default keywords for categorization
        self.categories = {
            'Groceries': [r'tesco', r'asda', r'sainsbury', r'aldi', r'lidl', r'waitrose', r'ocado'],
            'Dining': [r'mcdonald', r'deliveroo', r'just eat', r'ubereats', r'starbucks', r'costa'],
            'Subscriptions': [r'netflix', r'spotify', r'amazon prime', r'disney', r'apple.com', r'google'],
            'Bills/Utilities': [r'council tax', r'water', r'electric', r'gas', r'internet', r'mobile', r'rent'],
            'Transport': [r'uber', r'tfl', r'trainline', r'shell', r'bp', r'petrol'],
            'Shopping': [r'amazon', r'ebay', r'argos', r'boots', r'ikea'],
            'Entertainment': [r'steam', r'playstation', r'xbox', r'cinema', r'pub', r'bar']
        }

    def parse_pdf(self, file_path: str) -> pd.DataFrame:
        """
        Extracts table data from a PDF statement.
        """
        all_data = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        all_data.extend(table)
            
            if not all_data:
                return pd.DataFrame()

            # Attempt to find headers and clean data
            df = pd.DataFrame(all_data[1:], columns=all_data[0])
            return self._standardize_df(df)
        except Exception as e:
            print(f"Error parsing PDF: {e}")
            return pd.DataFrame()

    def parse_csv(self, file_path: str) -> pd.DataFrame:
        try:
            df = pd.read_csv(file_path)
            return self._standardize_df(df)
        except Exception as e:
            print(f"Error parsing CSV: {e}")
            return pd.DataFrame()

    def _standardize_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # Standardization logic
        col_map = {
            'Date': ['date', 'transaction date', 'posted date', 'when'],
            'Description': ['description', 'narrow description', 'transaction', 'details', 'info'],
            'Amount': ['amount', 'value', 'transaction amount', 'credit/debit', 'money']
        }
        
        standardized_cols = {}
        for target, alternatives in col_map.items():
            for col in df.columns:
                if col and str(col).lower() in alternatives:
                    standardized_cols[col] = target
                    break
        
        df = df.rename(columns=standardized_cols)
        required = ['Date', 'Description', 'Amount']
        
        # Filter for required columns if they exist
        existing = [col for col in required if col in df.columns]
        if not existing:
            return pd.DataFrame()
            
        df = df[existing]
        
        # Fill missing Amount/Date if possible or drop
        df = df.dropna(subset=['Description'])
        if 'Amount' in df.columns:
            # Clean amount strings (remove currency symbols)
            df['Amount'] = df['Amount'].replace(r'[£$,]', '', regex=True).astype(float, errors='ignore')
        
        if 'Description' in df.columns:
            df['Category'] = df['Description'].apply(self._categorize)
            
        return df

    def _categorize(self, description: str) -> str:
        description = str(description).lower()
        for cat, patterns in self.categories.items():
            for pattern in patterns:
                if re.search(pattern, description):
                    return cat
        return 'Other'

    def get_spending_insights(self, df: pd.DataFrame) -> Dict:
        """
        Returns insights like total spent per category and potential savings.
        """
        if df.empty:
            return {}
            
        summary = df.groupby('Category')['Amount'].sum().to_dict()
        
        # Simple logic: Highlight categories where spending is high
        # Or identify recurring small payments that add up
        
        insights = {
            "summary": summary,
            "total_spent": df['Amount'].sum(),
            "highest_category": max(summary, key=summary.get) if summary else "None"
        }
        
        return insights
