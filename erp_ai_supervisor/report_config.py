# report_config.py
"""
Report metadata and configuration for Vector DB semantic search.
Single source of truth for all supported ERP reports.
"""

# ============================================================
# REPORT METADATA - For Vector Database Embedding
# ============================================================
REPORT_DEFINITIONS = {
    "Balance Sheet": {
        "erp_name": "Balance Sheet",
        "description": (
            "Balance Sheet. Financial statement showing assets, liabilities, and equity. "
            "Shows company net worth, total assets, current assets, fixed assets, total liabilities, loans, debt, capital, "
            "shareholder equity, and opening. Use for: How much is the company worth? "
            "What are total assets? Total liabilities? Capital accounts? Assets and liabilities breakdown?"
        ),
        "aliases": ["balance sheet", "bs"],
        "keywords": [
            "capital account", "capital", "loan", "loans", "liability", "liabilities",
            "current liabilities", "fixed assets", "current assets", "opening balance",
            "current period", "difference in opening balances", "assets", "liabilities"
        ]
    },
    "Profit and Loss": {
        "erp_name": "Profit & Loss A/c",
        "description": (
            "Profit and Loss Account. Income statement showing revenues, expenses, and profit/loss. "
            "Displays gross profit, net profit, cost of sales, direct incomes/expenses, indirect incomes/expenses, "
            "sales revenue, and purchase accounts. Use for: What is the net profit? Revenue? Expenses? "
            "Gross profit? Cost of goods sold? Gross Loss?"
        ),
        "aliases": ["profit and loss", "p&l"],
        "keywords": [
            "opening stock", "closing stock", "purchase accounts", "purchases",
            "sales accounts", "sales", "gross profit", "net profit", "nett profit",
            "indirect expenses", "indirect incomes"
        ]
    },
    "Stock Summary": {
        "erp_name": "Stock Summary",
        "description": (
            "Stock Summary. Inventory and stock report showing all items with quantities and values. "
            "inward movements, outward movements, stock quantity, "
            "stock value, rate, item details, and stock valuation. Use for: What is stock? "
            "How many units of item X? Stock value? Inventory count? Stock items?"
        ),
        "aliases": ["stock summary", "inventory"],
        "keywords": [
            "quantity", "qty", "rate", "value", "pcs", "pieces", "stock items", 
            "quantities", "stock", "stock item"
        ]
    },
    "Day Book": {
        "erp_name": "Day Book",
        "description": (
            
        ),
        "aliases": ["day book", "daybook"],
        "keywords": [
            "particulars", "vch type", "vch no", "vch num", "inwards qty", "",
            "debit amount", "credit amount", "day book"
        ]
    },
    "Sales Register": {
        "erp_name": "Sales Register",
        "description": (
            "Sales Register. Summary of all sales transactions and invoices. "
            "Displays monthly sales performance, invoice values, transaction list, "
            "and period-wise sales breakdown with running closing balance (cumulative sales total per month). "
            "Use for: Total sales for a month? Monthly sales performance? Transaction summary? "
            "How much is the running closing balance (month-end cumulative sales)? "
            "Month-by-month sales comparison? Sales credit and closing balance trends?"
        ),
        "aliases": ["sales register", "sales"],
        "keywords": [
            "closing balance", "transaction", "transactions", "month-by-month", "monthly sales",
            "trnsaction", "credit", "debit", "sales register", "sales trend", "sales monthly"
        ]
    },
    "Bills Receivable": {
        "erp_name": "Bills Receivable",
        "description": (
            "Bills Receivable. Outstanding customer invoices and pending payments. "
            "Shows money owed to the business, customer names (debtors), pending amounts, "
            "overdue invoices, and receivable details. Use for: Who owes us money? "
            "Outstanding bills? Debtors list? Pending payments? Money incoming?"
        ),
        "aliases": ["bills receivable", "receivable"],
        "keywords": [
            "party", "party name", "pending amount", "pending", "due", "overdue",
            "receivable", "bills receivable"
        ]
    },
    "Cash Flow": {
        "erp_name": "Cash Flow",
        "description": (
            "Cash Flow. Analysis of cash inflows and outflows in the business. "
            "Shows cash movements, liquidity, operating cash flows, investing cash flows, "
            "financing cash flows, and net cash position. Use for: What is the cash inflow? "
            "Cash outflow? Net cash flow? Is the business liquid? Cash movements? "
            "Operating vs financing cash?"
        ),
        "aliases": ["cash flow", "cashflow"],
        "keywords": [
            "inflow", "outflow", "nettflow", "cash inflow", "cash outflow", 
            "net cash flow", "cash flow", "cashflow", "operating cash", "financing cash",
            "investing cash", "liquidity", "cash position"
        ]
    }
}

# ============================================================
# ERP XML NAME MAPPING
# ============================================================
# Maps friendly names to exact ERP XML report names
ERP_XML_MAP = {
    "Balance Sheet": "Balance Sheet",
    "Profit and Loss": "Profit & Loss A/c",
    "Profit & Loss": "Profit & Loss A/c",
    "Stock Summary": "Stock Summary",
    "Day Book": "Day Book",
    "Sales Register": "Sales Register",
    "Bills Receivable": "Bills Receivable",
    "Cash Flow": "Cash Flow",
}

# ============================================================
# VALID REPORT NAMES (for validation)
# ============================================================
VALID_REPORTS = list(REPORT_DEFINITIONS.keys())