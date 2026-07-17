import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

class AnalyticsEngine:
    def __init__(self):
        pass

    def load_data(self, items: List[Dict[str, Any]]) -> pd.DataFrame:
        if not items:
            return pd.DataFrame()
        df = pd.DataFrame(items)
        # Convert numeric types
        if 'principal_amount' in df.columns:
            df['principal_amount'] = pd.to_numeric(df['principal_amount'], errors='coerce')
        if 'interest_rate' in df.columns:
            df['interest_rate'] = pd.to_numeric(df['interest_rate'], errors='coerce')
        
        # Convert dates
        if 'maturity_date' in df.columns:
            df['maturity_date'] = pd.to_datetime(df['maturity_date'])
            
        return df

    def calculate_days_to_maturity(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or 'maturity_date' not in df.columns:
            return df
        
        today = pd.to_datetime(datetime.now().date())
        df['days_to_maturity'] = (df['maturity_date'] - today).dt.days
        return df

    def get_portfolio_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty:
            return {
                "total_principal": 0,
                "weighted_avg_interest": 0,
                "active_deposits": 0
            }

        total_principal = df['principal_amount'].sum() if 'principal_amount' in df.columns else 0
        
        # Calculate weighted average interest
        if total_principal > 0 and 'interest_rate' in df.columns:
            df['weighted_interest'] = df['principal_amount'] * df['interest_rate']
            weighted_avg = df['weighted_interest'].sum() / total_principal
        else:
            weighted_avg = df['interest_rate'].mean() if 'interest_rate' in df.columns else 0

        return {
            "total_principal": float(total_principal),
            "weighted_avg_interest": float(weighted_avg),
            "active_deposits": len(df)
        }
