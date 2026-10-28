from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from zoneinfo import ZoneInfo


def month_bounds_utc(month: int, year: int, tz_name: str) -> Tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    start_date = datetime(year, month, 1, tzinfo=tz)
    if month < 12:
        end_date = datetime(year, month + 1, 1, tzinfo=tz)
    else:
        end_date = datetime(year + 1, 1, 1, tzinfo=tz)
    return start_date, end_date


async def calculate_monthly_revenue(property_id: str, tenant_id: str, month: int, year: int) -> Decimal:
    result = await calculate_total_revenue(property_id, tenant_id, month=month, year=year)
    return Decimal(result["total"])


async def calculate_total_revenue(
    property_id: str,
    tenant_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    from app.core.database_pool import db_pool
    from sqlalchemy import text

    if not db_pool.session_factory:
        await db_pool.initialize()

    if not db_pool.session_factory:
        raise Exception("Database pool not available")

    async with db_pool.get_session() as session:
        prop = (await session.execute(
            text("SELECT timezone FROM properties WHERE id = :property_id AND tenant_id = :tenant_id"),
            {"property_id": property_id, "tenant_id": tenant_id},
        )).fetchone()
        if not prop:
            raise LookupError(f"Property {property_id} not found for tenant {tenant_id}")

        sql = """
            SELECT
                SUM(total_amount) as total_revenue,
                COUNT(*) as reservation_count
            FROM reservations
            WHERE property_id = :property_id AND tenant_id = :tenant_id
        """
        params: Dict[str, Any] = {"property_id": property_id, "tenant_id": tenant_id}
        if month is not None and year is not None:
            params["start"], params["end"] = month_bounds_utc(month, year, prop.timezone)
            sql += " AND check_in_date >= :start AND check_in_date < :end"

        row = (await session.execute(text(sql), params)).fetchone()

    total = row.total_revenue or Decimal("0")
    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "total": str(total),
        "currency": "USD",
        "count": row.reservation_count,
    }
