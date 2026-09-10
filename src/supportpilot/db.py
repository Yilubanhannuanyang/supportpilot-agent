import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "supportpilot.db"


def ensure_orders_schema(cursor: sqlite3.Cursor) -> None:
    """Create the orders table and apply the one-time legacy column migration."""

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_name TEXT,
            product_name TEXT,
            payment_status TEXT,
            shipping_status TEXT,
            estimated_delivery TEXT
        )
        """
    )

    cursor.execute("PRAGMA table_info(orders)")
    columns = {row[1] for row in cursor.fetchall()}

    if "hours_since_payment" not in columns:
        cursor.execute(
            """
            ALTER TABLE orders
            ADD COLUMN hours_since_payment INTEGER NOT NULL DEFAULT 0
            """
        )


def ensure_tickets_schema(cursor: sqlite3.Cursor) -> None:
    """Create the tickets table required by ticket tools and workflows."""

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )


def init_db() -> None:
    """Ensure schemas exist and seed the small deterministic demo dataset."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    ensure_orders_schema(cursor)
    ensure_tickets_schema(cursor)

    cursor.executemany(
        """
        INSERT OR IGNORE INTO orders (
            order_id,
            customer_name,
            product_name,
            payment_status,
            shipping_status,
            estimated_delivery,
            hours_since_payment
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "A1001",
                "张三",
                "无线蓝牙耳机",
                "已付款",
                "等待仓库发货",
                "预计 2 天内发货",
                72,
            ),
            (
                "A1002",
                "李四",
                "机械键盘",
                "已付款",
                "运输中",
                "预计明天送达",
                30,
            ),
            (
                "A1003",
                "王五",
                "27 英寸显示器",
                "已付款",
                "已签收",
                "已于昨日送达",
                96,
            ),
            (
                "A1004",
                "赵六",
                "智能手环",
                "已付款",
                "等待仓库发货",
                "预计尽快发货",
                60,
            ),
        ],
    )

    conn.commit()
    conn.close()


def get_order_from_db(order_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

          
    cursor.execute(
        """
        SELECT
            order_id,
            customer_name,
            product_name,
            payment_status,
            shipping_status,
            estimated_delivery,
            hours_since_payment
        FROM orders
        WHERE order_id = ?
        """,
        (order_id,),
    )
       

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "order_id": row[0],
        "customer_name": row[1],
        "product_name": row[2],
        "payment_status": row[3],
        "shipping_status": row[4],
        "estimated_delivery": row[5],
        "hours_since_payment": row[6],
    }
def create_ticket_in_db(
    order_id: str,
    issue_type: str,
    description: str,
) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO tickets (
            order_id,
            issue_type,
            description,
            status
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            order_id,
            issue_type,
            description,
            "已创建",
        ),
    )

    ticket_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return ticket_id
def get_ticket_from_db(ticket_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            ticket_id,
            order_id,
            issue_type,
            description,
            status
        FROM tickets
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "ticket_id": row[0],
        "order_id": row[1],
        "issue_type": row[2],
        "description": row[3],
        "status": row[4],
    }
def update_ticket_status_in_db(
    ticket_id: int,
    new_status: str,
) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tickets
        SET status = ?
        WHERE ticket_id = ?
        """,
        (
            new_status,
            ticket_id,
        ),
    )

    updated = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return updated
def find_open_ticket_by_order_and_type(
    order_id: str,
    issue_type: str,
) -> dict | None:
    """查找同一订单下尚未解决的同类型工单。"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            ticket_id,
            order_id,
            issue_type,
            description,
            status
        FROM tickets
        WHERE order_id = ?
          AND issue_type = ?
          AND status != '已解决'
        ORDER BY ticket_id DESC
        LIMIT 1
        """,
        (
            order_id,
            issue_type,
        ),
    )

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "ticket_id": row[0],
        "order_id": row[1],
        "issue_type": row[2],
        "description": row[3],
        "status": row[4],
    }
