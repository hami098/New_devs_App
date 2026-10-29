from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from app.services.cache import get_revenue_summary
from app.services.reservations import MixedCurrencyError, list_properties
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    
    if (month is None) != (year is None):
        raise HTTPException(status_code=422, detail="month and year must be given together")
    
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="No tenant is assigned to this user")
    
    try:
        revenue_data = await get_revenue_summary(property_id, tenant_id, month, year)
    except MixedCurrencyError:
        raise HTTPException(status_code=409, detail="Reservations of this property are in more than one currency")
    except Exception as e:
        print(f"Revenue summary failed for {property_id} (tenant: {tenant_id}): {e}")
        raise HTTPException(status_code=503, detail="Revenue data is temporarily unavailable")
    
    if revenue_data is None:
        raise HTTPException(status_code=404, detail="Property not found")
    
    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": revenue_data['total'],
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }

@router.get("/dashboard/properties")
async def get_dashboard_properties(
    current_user: dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="No tenant is assigned to this user")

    try:
        return await list_properties(tenant_id)
    except Exception as e:
        print(f"Property list failed (tenant: {tenant_id}): {e}")
        raise HTTPException(status_code=503, detail="Properties are temporarily unavailable")
