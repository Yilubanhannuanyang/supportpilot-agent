import sqlite3
from pathlib import Path

# 项目根目录：src/supportpilot/db.py -> parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# 演示用 SQLite 文件，随首次运行自动创建
DB_PATH = PROJECT_ROOT / "supportpilot.db"


def ensure_orders_schema(cursor: sqlite3.Cursor) -> None:
    """Create the orders table and apply the one-time legacy column migration."""

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY, --订单号
            customer_name TEXT, --客户名称
            product_name TEXT, --产品名称
            payment_status TEXT, --支付状态
            shipping_status TEXT, --运输状态
            estimated_delivery TEXT --预计送达时间
        )
        """
    )

    # hours_since_payment 是后加的列，老库需要就地补上，避免手动删库重建。
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
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, --工单ID
            order_id TEXT NOT NULL, --订单号
            issue_type TEXT NOT NULL, --问题类型
            description TEXT NOT NULL, --问题描述
            status TEXT NOT NULL --工单状态
        )
        """
    )


def init_db() -> None:
    """Ensure schemas exist and seed the small deterministic demo dataset."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    ensure_orders_schema(cursor)
    ensure_tickets_schema(cursor)

    # INSERT OR IGNORE 让初始化可重复执行：订单号已存在时跳过，不报错也不覆盖。
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
    """按订单号查询订单信息；不存在时返回 None。"""

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

    # 转成字典返回，便于工具层和模型直接按字段名读取。
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
    """插入一张工单并返回其自增主键。"""

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

    # lastrowid 是本次插入生成的自增 ID，供调用方后续引用这张工单。
    ticket_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return ticket_id


def get_ticket_from_db(ticket_id: int) -> dict | None:
    """按工单 ID 查询工单信息；不存在时返回 None。"""

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
    """更新工单状态；返回是否真的命中了记录。"""

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

    # rowcount > 0 表示确实改到了记录，否则说明工单不存在。
    updated = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return updated


def find_open_ticket_by_order_and_type(
    order_id: str,
    issue_type: str,
) -> dict | None:
    """查找同一订单下未解决的同类型工单。

    用于幂等控制：命中时说明已有在办工单，不必重复创建。
    """

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 排除「已解决」，并按工单 ID 倒序取最新的一条。
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
