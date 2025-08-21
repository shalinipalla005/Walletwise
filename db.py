import os
import sqlite3
import datetime as dt
from typing import Any, Dict, List, Optional , Tuple


DB_PATH = os.getenv("EXPENSE_TRACKER_DB", os.path.join(os.getcwd(), "expense_tracker.db"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cur.fetchall()]
    return column_name in columns


def _add_column_if_missing(conn: sqlite3.Connection, table_name: str, column_name: str, column_def: str):
    """Add a column to a table if it doesn't exist"""
    if not _column_exists(conn, table_name, column_name):
        try:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
            conn.commit()
        except sqlite3.Error as e:
            print(f"Warning: Could not add column {column_name} to {table_name}: {e}")


def init_db() -> None:
    """Initialize database with enhanced group expenses schema"""
    conn = _connect()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS group_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            payer_id INTEGER NOT NULL,
            category TEXT DEFAULT 'General',
            date TEXT NOT NULL,
            description TEXT,
            currency TEXT DEFAULT 'INR',
            is_settled INTEGER DEFAULT 0,
            settled_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (payer_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS group_expense_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_expense_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            share_amount REAL NOT NULL,
            is_settled INTEGER DEFAULT 0,
            settled_at TEXT,
            settlement_method TEXT,
            settlement_reference TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (group_expense_id) REFERENCES group_expenses(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(group_expense_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS group_settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER NOT NULL,
            to_user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'INR',
            settlement_date TEXT NOT NULL,
            method TEXT,
            reference TEXT,
            description TEXT,
            related_expense_ids TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (from_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (to_user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            category TEXT,
            date TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('Expense','Income')),
            payment_method TEXT,
            tags TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            year_month TEXT NOT NULL,
            category TEXT,
            amount REAL NOT NULL,
            UNIQUE(user_id, year_month, category),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- Indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_txn_user_date ON transactions(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_txn_user_cat ON transactions(user_id, category);
        CREATE INDEX IF NOT EXISTS idx_group_exp_payer ON group_expenses(payer_id, date);
        CREATE INDEX IF NOT EXISTS idx_group_shares_user ON group_expense_shares(user_id, is_settled);
        CREATE INDEX IF NOT EXISTS idx_group_shares_expense ON group_expense_shares(group_expense_id);
        CREATE INDEX IF NOT EXISTS idx_settlements_users ON group_settlements(from_user_id, to_user_id);
        """
    )
    
    # Add missing columns to existing tables
    _add_column_if_missing(conn, "group_expenses", "currency", "currency TEXT DEFAULT 'INR'")
    _add_column_if_missing(conn, "group_expenses", "is_settled", "is_settled INTEGER DEFAULT 0")
    _add_column_if_missing(conn, "group_expenses", "settled_at", "settled_at TEXT")
    _add_column_if_missing(conn, "group_expenses", "created_at", "created_at TEXT NOT NULL DEFAULT (datetime('now'))")
    _add_column_if_missing(conn, "group_expenses", "updated_at", "updated_at TEXT NOT NULL DEFAULT (datetime('now'))")
    
    _add_column_if_missing(conn, "group_expense_shares", "is_settled", "is_settled INTEGER DEFAULT 0")
    _add_column_if_missing(conn, "group_expense_shares", "settled_at", "settled_at TEXT")
    _add_column_if_missing(conn, "group_expense_shares", "settlement_method", "settlement_method TEXT")
    _add_column_if_missing(conn, "group_expense_shares", "settlement_reference", "settlement_reference TEXT")
    _add_column_if_missing(conn, "group_expense_shares", "created_at", "created_at TEXT NOT NULL DEFAULT (datetime('now'))")
    _add_column_if_missing(conn, "group_expense_shares", "updated_at", "updated_at TEXT NOT NULL DEFAULT (datetime('now'))")
    
    # Create or recreate triggers
    try:
        cur.execute("DROP TRIGGER IF EXISTS update_group_expenses_timestamp")
        cur.execute("DROP TRIGGER IF EXISTS update_group_shares_timestamp")
        
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS update_group_expenses_timestamp 
            AFTER UPDATE ON group_expenses
            BEGIN
                UPDATE group_expenses SET updated_at = datetime('now') WHERE id = NEW.id;
            END
        """)
        
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS update_group_shares_timestamp 
            AFTER UPDATE ON group_expense_shares
            BEGIN
                UPDATE group_expense_shares SET updated_at = datetime('now') WHERE id = NEW.id;
            END
        """)
    except sqlite3.Error as e:
        print(f"Warning: Could not create triggers: {e}")
    
    conn.commit()
    conn.close()


# ---------- User operations ---------- #
def create_user(name: str, email: str, password_hash: str) -> int:
    """Create a new user with validation"""
    if not name.strip():
        raise ValueError("Name cannot be empty")
    if not email.strip():
        raise ValueError("Email cannot be empty")
    if len(password_hash) < 6:
        raise ValueError("Password hash too short")
    
    conn = _connect()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users(name, email, password_hash) VALUES(?,?,?)",
            (name.strip(), email.lower().strip(), password_hash),
        )
        conn.commit()
        user_id = cur.lastrowid
        return int(user_id)
    except sqlite3.IntegrityError:
        raise ValueError("Email already exists")
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    """Get user by email with validation"""
    if not email.strip():
        return None
    
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = cur.fetchone()
    conn.close()
    return row


def update_user_password(user_id: int, new_hash: str) -> None:
    """Update user password with validation"""
    if len(new_hash) < 6:
        raise ValueError("Password hash too short")
    
    conn = _connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
    if cur.rowcount == 0:
        raise ValueError("User not found")
    conn.commit()
    conn.close()


# Transaction operations
def add_transaction(
    user_id: int,
    amount: float,
    description: Optional[str],
    category: Optional[str],
    date: dt.date,
    txn_type: str,
    payment_method: Optional[str],
    tags: Optional[str],
) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO transactions(user_id, amount, description, category, date, type, payment_method, tags)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            user_id,
            amount,
            (description or None),
            (category or None),
            date.isoformat(),
            txn_type,
            (payment_method or None),
            (tags or None),
        ),
    )
    conn.commit()
    txn_id = cur.lastrowid
    conn.close()
    return int(txn_id)


def update_transaction(
    txn_id: int,
    user_id: int,
    amount: float,
    description: Optional[str],
    category: Optional[str],
    date: dt.date,
    txn_type: str,
    payment_method: Optional[str],
    tags: Optional[str],
) -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE transactions
           SET amount = ?, description = ?, category = ?, date = ?, type = ?, payment_method = ?, tags = ?
         WHERE id = ? AND user_id = ?
        """,
        (
            amount,
            (description or None),
            (category or None),
            date.isoformat(),
            txn_type,
            (payment_method or None),
            (tags or None),
            txn_id,
            user_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_transaction(txn_id: int, user_id: int) -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (txn_id, user_id))
    conn.commit()
    conn.close()


def list_transactions(
    user_id: int,
    start_date: dt.date,
    end_date: dt.date,
    category: Optional[str] = None,
    txn_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    query = [
        "SELECT id, user_id, amount, description, category, date, type, payment_method, tags FROM transactions",
        "WHERE user_id = ? AND date BETWEEN ? AND ?",
    ]
    params: List[Any] = [user_id, start_date.isoformat(), end_date.isoformat()]
    if category:
        query.append("AND category = ?")
        params.append(category)
    if txn_type:
        query.append("AND type = ?")
        params.append(txn_type)
    query.append("ORDER BY date DESC, id DESC")
    cur.execute(" ".join(query), params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_distinct_categories(user_id: int) -> List[str]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT COALESCE(category,'Uncategorized') AS category FROM transactions WHERE user_id = ? ORDER BY 1",
        (user_id,),
    )
    rows = [r["category"] for r in cur.fetchall()]
    conn.close()
    return rows


# Budget operations
def set_budget(user_id: int, year_month: str, category: Optional[str], amount: float) -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO budgets(user_id, year_month, category, amount)
        VALUES(?,?,?,?)
        ON CONFLICT(user_id, year_month, category)
        DO UPDATE SET amount=excluded.amount
        """,
        (user_id, year_month, category, amount),
    )
    conn.commit()
    conn.close()


def get_budget(user_id: int, year_month: str, category: Optional[str]) -> Optional[float]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT amount FROM budgets WHERE user_id = ? AND year_month = ? AND category IS ?",
        (user_id, year_month, category),
    )
    row = cur.fetchone()
    conn.close()
    return float(row["amount"]) if row else None


def get_all_users() -> List[Dict[str, Any]]:
    """Get all users for sharing options"""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email FROM users ORDER BY name")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ==================== GROUP EXPENSE OPERATIONS ====================

def add_group_expense(
    title: str,
    amount: float,
    payer_id: int,
    category: str,
    date: dt.date,
    description: str,
    shares: List[Dict[str, Any]],
    currency: str = "INR"
) -> int:
    """Add a new group expense with shares"""
    conn = _connect()
    cur = conn.cursor()
    
    try:
        # Validate shares sum equals total amount
        total_shares = sum(share["amount"] for share in shares)
        if abs(total_shares - amount) > 0.01:
            raise ValueError(f"Shares total ({total_shares}) doesn't match expense amount ({amount})")
        
        # Check if currency column exists
        has_currency = _column_exists(conn, "group_expenses", "currency")
        has_created_at = _column_exists(conn, "group_expenses", "created_at")
        has_updated_at = _column_exists(conn, "group_expenses", "updated_at")
        
        # Build insert query based on available columns
        base_columns = "title, amount, payer_id, category, date, description"
        base_values = "?,?,?,?,?,?"
        base_params = [title, amount, payer_id, category, date.isoformat(), description]
        
        if has_currency:
            base_columns += ", currency"
            base_values += ",?"
            base_params.append(currency)
        
        if has_created_at:
            base_columns += ", created_at"
            base_values += ",?"
            base_params.append(dt.datetime.now().isoformat())
            
        if has_updated_at:
            base_columns += ", updated_at"
            base_values += ",?"
            base_params.append(dt.datetime.now().isoformat())
        
        cur.execute(
            f"INSERT INTO group_expenses({base_columns}) VALUES({base_values})",
            base_params
        )
        
        expense_id = cur.lastrowid
        
        # Insert shares
        has_share_created_at = _column_exists(conn, "group_expense_shares", "created_at")
        has_share_updated_at = _column_exists(conn, "group_expense_shares", "updated_at")
        
        share_columns = "group_expense_id, user_id, share_amount"
        share_values = "?,?,?"
        
        if has_share_created_at:
            share_columns += ", created_at"
            share_values += ",?"
            
        if has_share_updated_at:
            share_columns += ", updated_at"
            share_values += ",?"
        
        for share in shares:
            share_params = [expense_id, share["user_id"], share["amount"]]
            if has_share_created_at:
                share_params.append(dt.datetime.now().isoformat())
            if has_share_updated_at:
                share_params.append(dt.datetime.now().isoformat())
                
            cur.execute(
                f"INSERT INTO group_expense_shares({share_columns}) VALUES({share_values})",
                share_params
            )
        
        conn.commit()
        return int(expense_id)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# def get_group_expenses(user_id: int, limit: Optional[int] = None, include_settled: bool = True) -> List[Dict[str, Any]]:
#     """Get all group expenses for a user with enhanced details"""
#     conn = _connect()
#     cur = conn.cursor()
    
#     # Build column list based on what exists
#     has_currency = _column_exists(conn, "group_expenses", "currency")
#     has_is_settled = _column_exists(conn, "group_expenses", "is_settled")
#     has_settled_at = _column_exists(conn, "group_expenses", "settled_at")
#     has_share_settled = _column_exists(conn, "group_expense_shares", "is_settled")
#     has_settlement_method = _column_exists(conn, "group_expense_shares", "settlement_method")
#     has_settlement_ref = _column_exists(conn, "group_expense_shares", "settlement_reference")
    
#     select_cols = """
#         ge.id AS expense_id,
#         ge.title,
#         ge.amount,
#         ge.category,
#         ge.date,
#         ge.description,
#         ge.payer_id,
#         u.name AS payer_name,
#         u.email AS payer_email,
#         ges.id AS share_id,
#         ges.user_id AS share_user_id,
#         ges.share_amount
#     """
    
#     if has_currency:
#         select_cols += ", ge.currency"
#     else:
#         select_cols += ", 'INR' as currency"
        
#     if has_is_settled:
#         select_cols += ", ge.is_settled AS expense_settled"
#     else:
#         select_cols += ", 0 as expense_settled"
        
#     if has_settled_at:
#         select_cols += ", ge.settled_at AS expense_settled_at"
#     else:
#         select_cols += ", NULL as expense_settled_at"
        
#     if has_share_settled:
#         select_cols += ", ges.is_settled AS share_settled"
#     else:
#         select_cols += ", 0 as share_settled"
        
#     if has_settled_at:
#         select_cols += ", ges.settled_at AS share_settled_at"
#     else:
#         select_cols += ", NULL as share_settled_at"
        
#     if has_settlement_method:
#         select_cols += ", ges.settlement_method"
#     else:
#         select_cols += ", NULL as settlement_method"
        
#     if has_settlement_ref:
#         select_cols += ", ges.settlement_reference"
#     else:
#         select_cols += ", NULL as settlement_reference"
    
#     query = f"""
#         SELECT DISTINCT {select_cols}
#         FROM group_expenses ge
#         JOIN users u ON ge.payer_id = u.id
#         LEFT JOIN group_expense_shares ges ON ge.id = ges.group_expense_id
#         WHERE (ges.user_id = ? OR ge.payer_id = ?)
#     """
    
#     params = [user_id, user_id]
    
#     if not include_settled and has_is_settled and has_share_settled:
#         query += " AND (ge.is_settled = 0 OR ges.is_settled = 0)"
    
#     query += " ORDER BY ge.date DESC, ge.id DESC"
    
#     if limit:
#         query += f" LIMIT {limit}"
    
#     try:
#         cur.execute(query, params)
#         rows = cur.fetchall()
#         conn.close()
        
#         # Group results by expense
#         expenses_dict = {}
#         for row in rows:
#             expense_id = row['expense_id']
#             if expense_id not in expenses_dict:
#                 expenses_dict[expense_id] = {
#                     'id': row['expense_id'],
#                     'expense_id': row['expense_id'],
#                     'title': row['title'],
#                     'amount': row['amount'],
#                     'category': row['category'],
#                     'date': row['date'],
#                     'description': row['description'],
#                     'payer_id': row['payer_id'],
#                     'payer_name': row['payer_name'],
#                     'payer_email': row['payer_email'],
#                     'currency': row.get('currency', 'INR'),
#                     'is_settled': row.get('expense_settled', 0),
#                     'settled_at': row.get('expense_settled_at'),
#                     'shares': []
#                 }
            
#             # Add share info if exists
#             if row.get('share_id'):
#                 share_info = {
#                     'share_id': row['share_id'],
#                     'user_id': row['share_user_id'],
#                     'share_amount': row['share_amount'],
#                     'is_settled': row.get('share_settled', 0),
#                     'settled_at': row.get('share_settled_at'),
#                     'settlement_method': row.get('settlement_method'),
#                     'settlement_reference': row.get('settlement_reference')
#                 }
                
#                 # Add user's share amount for compatibility
#                 if row['share_user_id'] == user_id:
#                     expenses_dict[expense_id]['share_amount'] = row['share_amount']
#                     expenses_dict[expense_id]['share_settled'] = row.get('share_settled', 0)
                
#                 expenses_dict[expense_id]['shares'].append(share_info)
        
#         return list(expenses_dict.values())
        
#     except Exception as e:
#         conn.close()
#         print(f"Error in get_group_expenses: {e}")
#         return []
def get_group_expenses(user_id: int, limit: Optional[int] = None, include_settled: bool = True) -> List[Dict[str, Any]]:
    """Get all group expenses for a user with enhanced details"""
    conn = _connect()
    cur = conn.cursor()
    
    # Build column list based on what exists
    has_currency = _column_exists(conn, "group_expenses", "currency")
    has_is_settled = _column_exists(conn, "group_expenses", "is_settled")
    has_settled_at = _column_exists(conn, "group_expenses", "settled_at")
    has_share_settled = _column_exists(conn, "group_expense_shares", "is_settled")
    has_settlement_method = _column_exists(conn, "group_expense_shares", "settlement_method")
    has_settlement_ref = _column_exists(conn, "group_expense_shares", "settlement_reference")
    
    select_cols = """
        ge.id AS expense_id,
        ge.title,
        ge.amount,
        ge.category,
        ge.date,
        ge.description,
        ge.payer_id,
        u.name AS payer_name,
        u.email AS payer_email,
        ges.id AS share_id,
        ges.user_id AS share_user_id,
        ges.share_amount
    """
    
    if has_currency:
        select_cols += ", ge.currency"
    else:
        select_cols += ", 'INR' as currency"
        
    if has_is_settled:
        select_cols += ", ge.is_settled AS expense_settled"
    else:
        select_cols += ", 0 as expense_settled"
        
    if has_settled_at:
        select_cols += ", ge.settled_at AS expense_settled_at"
    else:
        select_cols += ", NULL as expense_settled_at"
        
    if has_share_settled:
        select_cols += ", ges.is_settled AS share_settled"
    else:
        select_cols += ", 0 as share_settled"
        
    if has_settled_at:
        select_cols += ", ges.settled_at AS share_settled_at"
    else:
        select_cols += ", NULL as share_settled_at"
        
    if has_settlement_method:
        select_cols += ", ges.settlement_method"
    else:
        select_cols += ", NULL as settlement_method"
        
    if has_settlement_ref:
        select_cols += ", ges.settlement_reference"
    else:
        select_cols += ", NULL as settlement_reference"
    
    query = f"""
        SELECT DISTINCT {select_cols}
        FROM group_expenses ge
        JOIN users u ON ge.payer_id = u.id
        LEFT JOIN group_expense_shares ges ON ge.id = ges.group_expense_id
        WHERE (ges.user_id = ? OR ge.payer_id = ?)
    """
    
    params = [user_id, user_id]
    
    if not include_settled and has_is_settled and has_share_settled:
        query += " AND (ge.is_settled = 0 OR ges.is_settled = 0)"
    
    query += " ORDER BY ge.date DESC, ge.id DESC"
    
    if limit:
        query += f" LIMIT {limit}"
    
    try:
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        
        # Group results by expense
        expenses_dict = {}
        for row in rows:
            # Convert row to dict for easier handling
            row_dict = dict(row)
            
            expense_id = row_dict['expense_id']
            if expense_id not in expenses_dict:
                expenses_dict[expense_id] = {
                    'id': row_dict['expense_id'],
                    'expense_id': row_dict['expense_id'],
                    'title': row_dict['title'],
                    'amount': row_dict['amount'],
                    'category': row_dict['category'],
                    'date': row_dict['date'],
                    'description': row_dict['description'],
                    'payer_id': row_dict['payer_id'],
                    'payer_name': row_dict['payer_name'],
                    'payer_email': row_dict['payer_email'],
                    'currency': row_dict.get('currency', 'INR'),
                    'is_settled': row_dict.get('expense_settled', 0),
                    'settled_at': row_dict.get('expense_settled_at'),
                    'shares': []
                }
            
            # Add share info if exists
            if row_dict.get('share_id'):
                share_info = {
                    'share_id': row_dict['share_id'],
                    'user_id': row_dict['share_user_id'],
                    'share_amount': row_dict['share_amount'],
                    'is_settled': row_dict.get('share_settled', 0),
                    'settled_at': row_dict.get('share_settled_at'),
                    'settlement_method': row_dict.get('settlement_method'),
                    'settlement_reference': row_dict.get('settlement_reference')
                }
                
                # Add user's share amount for compatibility
                if row_dict['share_user_id'] == user_id:
                    expenses_dict[expense_id]['share_amount'] = row_dict['share_amount']
                    expenses_dict[expense_id]['share_settled'] = row_dict.get('share_settled', 0)
                
                expenses_dict[expense_id]['shares'].append(share_info)
        
        return list(expenses_dict.values())
        
    except Exception as e:
        conn.close()
        print(f"Error in get_group_expenses: {e}")
        return []

def delete_group_expense(expense_id: int, payer_id: int) -> bool:
    """Delete a group expense (only by the payer)"""
    conn = _connect()
    cur = conn.cursor()
    
    try:
        # Verify ownership
        cur.execute(
            "SELECT payer_id FROM group_expenses WHERE id = ?",
            (expense_id,)
        )
        result = cur.fetchone()
        if not result or result['payer_id'] != payer_id:
            return False
        
        # Delete expense (shares will be deleted by foreign key cascade)
        cur.execute("DELETE FROM group_expenses WHERE id = ?", (expense_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting group expense: {e}")
        return False
    finally:
        conn.close()


def settle_expense_share(share_id: int, user_id: int, method: Optional[str] = None, 
                        reference: Optional[str] = None) -> bool:
    """Mark a specific user's share as settled"""
    conn = _connect()
    cur = conn.cursor()
    
    try:
        # Check which columns exist
        has_is_settled = _column_exists(conn, "group_expense_shares", "is_settled")
        has_settled_at = _column_exists(conn, "group_expense_shares", "settled_at")
        has_settlement_method = _column_exists(conn, "group_expense_shares", "settlement_method")
        has_settlement_ref = _column_exists(conn, "group_expense_shares", "settlement_reference")
        has_updated_at = _column_exists(conn, "group_expense_shares", "updated_at")
        
        if not has_is_settled:
            print("Warning: is_settled column not found, settlement may not work properly")
            return False
        
        # Verify the share belongs to the user
        cur.execute(
            "SELECT group_expense_id FROM group_expense_shares WHERE id = ? AND user_id = ?",
            (share_id, user_id)
        )
        result = cur.fetchone()
        if not result:
            return False
        
        group_expense_id = result['group_expense_id']
        
        # Build update query based on available columns
        update_parts = ["is_settled = 1"]
        params = []
        
        if has_settled_at:
            update_parts.append("settled_at = ?")
            params.append(dt.datetime.now().isoformat())
            
        if has_settlement_method and method:
            update_parts.append("settlement_method = ?")
            params.append(method)
            
        if has_settlement_ref and reference:
            update_parts.append("settlement_reference = ?")
            params.append(reference)
            
        if has_updated_at:
            update_parts.append("updated_at = ?")
            params.append(dt.datetime.now().isoformat())
        
        params.extend([share_id, user_id])
        
        # Mark share as settled
        cur.execute(
            f"""
            UPDATE group_expense_shares
            SET {', '.join(update_parts)}
            WHERE id = ? AND user_id = ?
            """,
            params
        )
        
        # Check if all shares are now settled
        if has_is_settled:
            cur.execute(
                """
                SELECT COUNT(*) as unsettled_count
                FROM group_expense_shares
                WHERE group_expense_id = ? AND is_settled = 0
                """,
                (group_expense_id,)
            )
            
            unsettled_count = cur.fetchone()['unsettled_count']
            
            # If all shares settled, mark the entire expense as settled
            if unsettled_count == 0:
                expense_has_is_settled = _column_exists(conn, "group_expenses", "is_settled")
                expense_has_settled_at = _column_exists(conn, "group_expenses", "settled_at")
                expense_has_updated_at = _column_exists(conn, "group_expenses", "updated_at")
                
                if expense_has_is_settled:
                    expense_update_parts = ["is_settled = 1"]
                    expense_params = []
                    
                    if expense_has_settled_at:
                        expense_update_parts.append("settled_at = ?")
                        expense_params.append(dt.datetime.now().isoformat())
                        
                    if expense_has_updated_at:
                        expense_update_parts.append("updated_at = ?")
                        expense_params.append(dt.datetime.now().isoformat())
                    
                    expense_params.append(group_expense_id)
                    
                    cur.execute(
                        f"""
                        UPDATE group_expenses
                        SET {', '.join(expense_update_parts)}
                        WHERE id = ?
                        """,
                        expense_params
                    )
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error settling expense share: {e}")
        return False
    finally:
        conn.close()


def settle_multiple_expenses(user_id: int, expense_ids: List[int], 
                           method: Optional[str] = None, 
                           reference: Optional[str] = None) -> Dict[str, Any]:
    """Settle multiple expenses for a user"""
    conn = _connect()
    cur = conn.cursor()
    
    settled_count = 0
    failed_count = 0
    settled_amount = 0.0
    
    try:
        has_is_settled = _column_exists(conn, "group_expense_shares", "is_settled")
        
        if not has_is_settled:
            return {
                'settled_count': 0,
                'failed_count': len(expense_ids),
                'settled_amount': 0.0
            }
        
        for expense_id in expense_ids:
            # Get the share for this expense and user
            cur.execute(
                """
                SELECT id, share_amount 
                FROM group_expense_shares 
                WHERE group_expense_id = ? AND user_id = ? AND is_settled = 0
                """,
                (expense_id, user_id)
            )
            
            share_row = cur.fetchone()
            if share_row:
                share_id = share_row['id']
                share_amount = share_row['share_amount']
                
                if settle_expense_share(share_id, user_id, method, reference):
                    settled_count += 1
                    settled_amount += share_amount
                else:
                    failed_count += 1
            else:
                failed_count += 1
        
        return {
            'settled_count': settled_count,
            'failed_count': failed_count,
            'settled_amount': settled_amount
        }
    except Exception as e:
        print(f"Error in settle_multiple_expenses: {e}")
        return {
            'settled_count': 0,
            'failed_count': len(expense_ids),
            'settled_amount': 0.0
        }
    finally:
        conn.close()


def get_user_balance_summary(user_id: int) -> Dict[str, Any]:
    """Get comprehensive balance summary for a user"""
    conn = _connect()
    cur = conn.cursor()
    
    try:
        has_is_settled = _column_exists(conn, "group_expense_shares", "is_settled")
        
        if not has_is_settled:
            # Return basic summary without settlement info
            cur.execute(
                "SELECT COALESCE(SUM(amount), 0) as total_paid FROM group_expenses WHERE payer_id = ?",
                (user_id,)
            )
            total_paid = cur.fetchone()['total_paid']
            
            return {
                'total_paid': total_paid,
                'total_share': 0,
                'total_owes': 0,
                'total_owed_to_user': 0,
                'net_balance': total_paid,
                'owes_to': [],
                'owed_by': []
            }
        
        # Get amounts user owes to others (where user didn't pay but has unsettled shares)
        cur.execute(
            """
            SELECT 
                ge.payer_id,
                u.name AS payer_name,
                SUM(ges.share_amount) AS total_owed
            FROM group_expense_shares ges
            JOIN group_expenses ge ON ges.group_expense_id = ge.id
            JOIN users u ON ge.payer_id = u.id
            WHERE ges.user_id = ? AND ges.is_settled = 0 AND ge.payer_id != ?
            GROUP BY ge.payer_id, u.name
            """,
            (user_id, user_id)
        )
        owes_to = [dict(row) for row in cur.fetchall()]
        total_owes = sum(item['total_owed'] for item in owes_to)
        
        # Get amounts others owe to user (where user paid but others have unsettled shares)
        cur.execute(
            """
            SELECT 
                ges.user_id,
                u.name AS user_name,
                SUM(ges.share_amount) AS total_owed_to_user
            FROM group_expense_shares ges
            JOIN group_expenses ge ON ges.group_expense_id = ge.id
            JOIN users u ON ges.user_id = u.id
            WHERE ge.payer_id = ? AND ges.is_settled = 0 AND ges.user_id != ?
            GROUP BY ges.user_id, u.name
            """,
            (user_id, user_id)
        )
        owed_by = [dict(row) for row in cur.fetchall()]
        total_owed_to_user = sum(item['total_owed_to_user'] for item in owed_by)
        
        # Get total expenses paid by user
        cur.execute(
            "SELECT COALESCE(SUM(amount), 0) as total_paid FROM group_expenses WHERE payer_id = ?",
            (user_id,)
        )
        total_paid = cur.fetchone()['total_paid']
        
        # Get total share amount for user
        cur.execute(
            """
            SELECT COALESCE(SUM(ges.share_amount), 0) as total_share
            FROM group_expense_shares ges
            JOIN group_expenses ge ON ges.group_expense_id = ge.id
            WHERE ges.user_id = ?
            """,
            (user_id,)
        )
        total_share = cur.fetchone()['total_share']
        
        net_balance = total_owed_to_user - total_owes
        
        return {
            'total_paid': total_paid,
            'total_share': total_share,
            'total_owes': total_owes,
            'total_owed_to_user': total_owed_to_user,
            'net_balance': net_balance,
            'owes_to': owes_to,
            'owed_by': owed_by
        }
        
    except Exception as e:
        print(f"Error in get_user_balance_summary: {e}")
        return {
            'total_paid': 0,
            'total_share': 0,
            'total_owes': 0,
            'total_owed_to_user': 0,
            'net_balance': 0,
            'owes_to': [],
            'owed_by': []
        }
    finally:
        conn.close()


def get_group_expense_statistics(user_id: int, days: int = 30) -> Dict[str, Any]:
    """Get statistics for group expenses"""
    conn = _connect()
    cur = conn.cursor()
    
    start_date = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    
    try:
        # Recent expenses count and amount
        cur.execute(
            """
            SELECT COUNT(DISTINCT ge.id) as count, COALESCE(SUM(ge.amount), 0) as total
            FROM group_expenses ge
            LEFT JOIN group_expense_shares ges ON ge.id = ges.group_expense_id
            WHERE (ge.payer_id = ? OR ges.user_id = ?) AND ge.date >= ?
            """,
            (user_id, user_id, start_date)
        )
        recent_stats = dict(cur.fetchone())
        
        # Category breakdown
        cur.execute(
            """
            SELECT 
                ge.category,
                COUNT(DISTINCT ge.id) as expense_count,
                SUM(CASE WHEN ge.payer_id = ? THEN ge.amount ELSE COALESCE(ges.share_amount, 0) END) as total_amount
            FROM group_expenses ge
            LEFT JOIN group_expense_shares ges ON ge.id = ges.group_expense_id AND ges.user_id = ?
            WHERE (ge.payer_id = ? OR ges.user_id = ?) AND ge.date >= ?
            GROUP BY ge.category
            ORDER BY total_amount DESC
            """,
            (user_id, user_id, user_id, user_id, start_date)
        )
        categories = [dict(row) for row in cur.fetchall()]
        
        return {
            'recent_expenses_count': recent_stats['count'],
            'recent_expenses_total': recent_stats['total'],
            'categories': categories,
            'period_days': days
        }
    except Exception as e:
        print(f"Error in get_group_expense_statistics: {e}")
        return {
            'recent_expenses_count': 0,
            'recent_expenses_total': 0,
            'categories': [],
            'period_days': days
        }
    finally:
        conn.close()


def get_unsettled_expenses_for_user(user_id: int) -> List[Dict[str, Any]]:
    """Get all unsettled expenses where user owes money"""
    conn = _connect()
    cur = conn.cursor()
    
    try:
        has_is_settled = _column_exists(conn, "group_expense_shares", "is_settled")
        has_created_at = _column_exists(conn, "group_expense_shares", "created_at")
        
        if not has_is_settled:
            return []
        
        select_cols = """
            ge.id AS expense_id,
            ge.title,
            ge.amount AS total_amount,
            ge.date,
            ge.payer_id,
            u.name AS payer_name,
            ges.id AS share_id,
            ges.share_amount
        """
        
        if has_created_at:
            select_cols += ", ges.created_at"
        else:
            select_cols += ", '' as created_at"
        
        cur.execute(
            f"""
            SELECT {select_cols}
            FROM group_expense_shares ges
            JOIN group_expenses ge ON ges.group_expense_id = ge.id
            JOIN users u ON ge.payer_id = u.id
            WHERE ges.user_id = ? AND ges.is_settled = 0 AND ge.payer_id != ?
            ORDER BY ge.date DESC
            """,
            (user_id, user_id)
        )
        
        rows = [dict(row) for row in cur.fetchall()]
        return rows
        
    except Exception as e:
        print(f"Error in get_unsettled_expenses_for_user: {e}")
        return []
    finally:
        conn.close()


# Additional helper functions with error handling

def validate_expense_shares(amount: float, shares: List[Dict[str, Any]], tolerance: float = 0.01) -> bool:
    """Validate that shares sum up to the total amount"""
    total_shares = sum(share.get("amount", 0) for share in shares)
    return abs(total_shares - amount) <= tolerance


def calculate_equal_shares(amount: float, user_count: int) -> float:
    """Calculate equal share amount for given users"""
    return round(amount / user_count, 2)


def get_quick_stats(user_id: int) -> Dict[str, Any]:
    """Get quick stats for dashboard display with error handling"""
    try:
        # Get basic balance summary
        balance_summary = get_user_balance_summary(user_id)
        
        # Get recent activity
        conn = _connect()
        cur = conn.cursor()
        
        thirty_days_ago = (dt.date.today() - dt.timedelta(days=30)).isoformat()
        
        cur.execute("""
            SELECT COUNT(DISTINCT ge.id) as recent_expense_count
            FROM group_expenses ge
            LEFT JOIN group_expense_shares ges ON ge.id = ges.group_expense_id
            WHERE (ge.payer_id = ? OR ges.user_id = ?) 
              AND ge.date >= ?
        """, (user_id, user_id, thirty_days_ago))
        
        recent_count = cur.fetchone()['recent_expense_count']
        
        # Get total lifetime expenses
        cur.execute("""
            SELECT COUNT(DISTINCT ge.id) as total_expense_count,
                   SUM(CASE WHEN ge.payer_id = ? THEN ge.amount ELSE 0 END) as total_paid
            FROM group_expenses ge
            LEFT JOIN group_expense_shares ges ON ge.id = ges.group_expense_id
            WHERE ge.payer_id = ? OR ges.user_id = ?
        """, (user_id, user_id, user_id))
        
        lifetime_stats = cur.fetchone()
        conn.close()
        
        return {
            'recent_expenses': recent_count,
            'pending_to_pay': balance_summary['total_owes'],
            'pending_to_receive': balance_summary['total_owed_to_user'],
            'net_balance': balance_summary['net_balance'],
            'total_lifetime_expenses': lifetime_stats['total_expense_count'],
            'total_lifetime_paid': lifetime_stats['total_paid'] or 0
        }
        
    except Exception as e:
        print(f"Error in get_quick_stats: {e}")
        return {
            'recent_expenses': 0,
            'pending_to_pay': 0,
            'pending_to_receive': 0,
            'net_balance': 0,
            'total_lifetime_expenses': 0,
            'total_lifetime_paid': 0
        }