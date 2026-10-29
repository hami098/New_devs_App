from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional

async def calculate_monthly_revenue(property_id: str, tenant_id: str, month: int, year: int) -> Optional[Dict[str, Any]]:
    """
    Calculates revenue for a specific month in the property's own time zone.
    """
    from app.core.database_pool import db_pool
    from sqlalchemy import text

    await db_pool.initialize()
    if not db_pool.session_factory:
        raise RuntimeError("Database pool not available")

    async with db_pool.get_session() as session:
        query = text("""
            SELECT
                COALESCE(SUM(r.total_amount), 0) AS total_revenue,
                COUNT(r.id) AS reservation_count
            FROM properties p
            LEFT JOIN reservations r
                ON r.property_id = p.id
                AND r.tenant_id = p.tenant_id
                AND r.check_in_date >= (make_date(:year, :month, 1)::timestamp AT TIME ZONE p.timezone)
                AND r.check_in_date < ((make_date(:year, :month, 1) + interval '1 month')::timestamp AT TIME ZONE p.timezone)
            WHERE p.id = :property_id AND p.tenant_id = :tenant_id
            GROUP BY p.id
        """)

        result = await session.execute(query, {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "month": month,
            "year": year
        })
        row = result.fetchone()
        if not row:
            return None

        total_revenue = Decimal(row.total_revenue).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": str(total_revenue),
            "currency": "USD",
            "count": row.reservation_count
        }

async def calculate_total_revenue(property_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """
    Aggregates revenue from database.
    """
    from app.core.database_pool import db_pool
    from sqlalchemy import text

    await db_pool.initialize()
    if not db_pool.session_factory:
        raise RuntimeError("Database pool not available")

    async with db_pool.get_session() as session:
        query = text("""
            SELECT
                COALESCE(SUM(r.total_amount), 0) AS total_revenue,
                COUNT(r.id) AS reservation_count
            FROM properties p
            LEFT JOIN reservations r
                ON r.property_id = p.id
                AND r.tenant_id = p.tenant_id
            WHERE p.id = :property_id AND p.tenant_id = :tenant_id
            GROUP BY p.id
        """)
        
        result = await session.execute(query, {
            "property_id": property_id, 
            "tenant_id": tenant_id
        })
        row = result.fetchone()
        if not row:
            return None

        total_revenue = Decimal(row.total_revenue).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": str(total_revenue),
            "currency": "USD",
            "count": row.reservation_count
        }


async def list_properties(tenant_id: str) -> List[Dict[str, Any]]:
    """
    Lists the tenant's own properties.
    """
    from app.core.database_pool import db_pool
    from sqlalchemy import text

    await db_pool.initialize()
    if not db_pool.session_factory:
        raise RuntimeError("Database pool not available")

    async with db_pool.get_session() as session:
        query = text("""
            SELECT id, name, timezone
            FROM properties
            WHERE tenant_id = :tenant_id
            ORDER BY name
        """)
        result = await session.execute(query, {"tenant_id": tenant_id})
        return [{"id": row.id, "name": row.name, "timezone": row.timezone} for row in result.fetchall()]
