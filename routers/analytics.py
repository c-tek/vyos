from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_
from typing import List, Optional
from models import ChangeJournal, Quota, ScheduledTask, NotificationRule, User, SubnetTrafficMetrics, Subnet
from config import get_async_db
from datetime import datetime, timedelta
from auth import get_current_active_user, RoleChecker
from schemas import SubnetTrafficMetricsResponse, SubnetTrafficSummary, SubnetTrafficTimeSeries, TimeSeriesDataPoint

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    dependencies=[Depends(get_current_active_user)]
)

@router.get("/usage", tags=["Analytics"])
async def get_usage_summary(
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    result = {}
    if user_id:
        scheduled_tasks_count = await db.scalar(select(func.count()).select_from(ScheduledTask).where(ScheduledTask.user_id == user_id))
        notification_rules_count = await db.scalar(select(func.count()).select_from(NotificationRule).where(NotificationRule.user_id == user_id))
    else:
        scheduled_tasks_count = await db.scalar(select(func.count()).select_from(ScheduledTask))
        notification_rules_count = await db.scalar(select(func.count()).select_from(NotificationRule))
    result["scheduled_tasks"] = scheduled_tasks_count or 0
    result["notification_rules"] = notification_rules_count or 0
    return result

@router.get("/activity", tags=["Analytics"])
async def get_activity_report(
    days: int = 7,
    db: AsyncSession = Depends(get_async_db)
):
    since = datetime.utcnow() - timedelta(days=days)
    query = select(ChangeJournal).where(ChangeJournal.timestamp >= since)
    result = await db.execute(query)
    entries = result.scalars().all()
    per_day = {}
    for entry in entries:
        day = entry.timestamp.date().isoformat()
        per_day[day] = per_day.get(day, 0) + 1
    return per_day

@router.get("/subnet-traffic/summary", response_model=List[SubnetTrafficSummary])
async def get_subnet_traffic_summary(
    subnet_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a summary of subnet traffic over the specified time period.
    
    Args:
        subnet_id: Optional filter for a specific subnet
        days: Number of days to include in the summary (default: 7, max: 90)
        
    Returns:
        List of subnet traffic summaries
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Build the query to get subnet info and aggregate metrics
    query = select(
        SubnetTrafficMetrics.subnet_id,
        Subnet.name.label("subnet_name"),
        Subnet.cidr.label("subnet_cidr"),
        func.sum(SubnetTrafficMetrics.rx_bytes).label("total_rx_bytes"),
        func.sum(SubnetTrafficMetrics.tx_bytes).label("total_tx_bytes"),
        func.avg(SubnetTrafficMetrics.rx_bytes).label("avg_rx_bytes"),
        func.avg(SubnetTrafficMetrics.tx_bytes).label("avg_tx_bytes"),
        func.max(SubnetTrafficMetrics.rx_bytes).label("peak_rx_bytes"),
        func.max(SubnetTrafficMetrics.tx_bytes).label("peak_tx_bytes"),
        func.avg(SubnetTrafficMetrics.active_hosts).label("avg_active_hosts"),
        func.max(SubnetTrafficMetrics.active_hosts).label("max_active_hosts")
    ).join(
        Subnet, SubnetTrafficMetrics.subnet_id == Subnet.id
    ).filter(
        SubnetTrafficMetrics.timestamp >= cutoff_date
    ).group_by(
        SubnetTrafficMetrics.subnet_id, Subnet.name, Subnet.cidr
    )
    
    if subnet_id:
        query = query.filter(SubnetTrafficMetrics.subnet_id == subnet_id)
    
    result = await db.execute(query)
    summary_data = result.fetchall()
    
    if not summary_data:
        # If no data is found, check if the subnet exists
        if subnet_id:
            subnet_result = await db.execute(select(Subnet).filter(Subnet.id == subnet_id))
            if not subnet_result.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subnet with ID {subnet_id} not found")
        
        return []
    
    # Calculate hourly averages and format response
    hours = days * 24
    summaries = []
    
    for row in summary_data:
        peak_time_query = select(SubnetTrafficMetrics.timestamp).filter(
            SubnetTrafficMetrics.subnet_id == row.subnet_id,
            SubnetTrafficMetrics.timestamp >= cutoff_date,
            SubnetTrafficMetrics.rx_bytes == row.peak_rx_bytes
        ).order_by(SubnetTrafficMetrics.timestamp).limit(1)
        
        peak_time_result = await db.execute(peak_time_query)
        peak_time = peak_time_result.scalar_one_or_none()
        
        summaries.append(SubnetTrafficSummary(
            subnet_id=row.subnet_id,
            subnet_name=row.subnet_name,
            subnet_cidr=row.subnet_cidr,
            total_rx_bytes=row.total_rx_bytes,
            total_tx_bytes=row.total_tx_bytes,
            avg_rx_bytes_per_hour=row.avg_rx_bytes,
            avg_tx_bytes_per_hour=row.avg_tx_bytes,
            peak_rx_bytes=row.peak_rx_bytes,
            peak_tx_bytes=row.peak_tx_bytes,
            peak_time=peak_time,
            avg_active_hosts=row.avg_active_hosts,
            max_active_hosts=row.max_active_hosts
        ))
    
    return summaries

@router.get("/subnet-traffic/timeseries", response_model=List[SubnetTrafficTimeSeries])
async def get_subnet_traffic_timeseries(
    metric: str = Query(..., description="Metric to retrieve: rx_bytes, tx_bytes, active_hosts"),
    interval: str = Query("hourly", description="Data interval: hourly or daily"),
    subnet_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get time series data for subnet traffic metrics.
    
    Args:
        metric: Which metric to retrieve (rx_bytes, tx_bytes, active_hosts)
        interval: Data interval (hourly or daily)
        subnet_id: Optional filter for a specific subnet
        days: Number of days to include in the data (default: 7, max: 90)
        
    Returns:
        List of time series data by subnet
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Validate metric
    valid_metrics = ["rx_bytes", "tx_bytes", "active_hosts"]
    if metric not in valid_metrics:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}")
    
    # Validate interval
    valid_intervals = ["hourly", "daily"]
    if interval not in valid_intervals:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail=f"Invalid interval. Must be one of: {', '.join(valid_intervals)}")
    
    # Define the date_trunc function based on the interval
    if interval == "hourly":
        # PostgreSQL syntax, adjust if using a different database
        date_func = func.date_trunc('hour', SubnetTrafficMetrics.timestamp)
        group_func = func.avg(getattr(SubnetTrafficMetrics, metric))
    else:  # daily
        date_func = func.date_trunc('day', SubnetTrafficMetrics.timestamp)
        group_func = func.sum(getattr(SubnetTrafficMetrics, metric))
    
    # Build the query
    query = select(
        SubnetTrafficMetrics.subnet_id,
        Subnet.name.label("subnet_name"),
        date_func.label("timestamp"),
        group_func.label("value")
    ).join(
        Subnet, SubnetTrafficMetrics.subnet_id == Subnet.id
    ).filter(
        SubnetTrafficMetrics.timestamp >= cutoff_date
    ).group_by(
        SubnetTrafficMetrics.subnet_id, Subnet.name, "timestamp"
    ).order_by(
        SubnetTrafficMetrics.subnet_id, "timestamp"
    )
    
    if subnet_id:
        query = query.filter(SubnetTrafficMetrics.subnet_id == subnet_id)
    
    result = await db.execute(query)
    timeseries_data = result.fetchall()
    
    # Group the results by subnet
    subnet_series = {}
    for row in timeseries_data:
        if row.subnet_id not in subnet_series:
            subnet_series[row.subnet_id] = {
                "subnet_id": row.subnet_id,
                "subnet_name": row.subnet_name,
                "metric": metric,
                "interval": interval,
                "data": []
            }
        
        subnet_series[row.subnet_id]["data"].append(TimeSeriesDataPoint(
            timestamp=row.timestamp,
            value=float(row.value)
        ))
    
    # Convert to list for response
    response = [SubnetTrafficTimeSeries(**series) for series in subnet_series.values()]
    
    return response

@router.get("/subnet-traffic/recent", response_model=List[SubnetTrafficMetricsResponse])
async def get_recent_subnet_traffic_metrics(
    subnet_id: Optional[int] = None,
    limit: int = Query(20, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the most recent traffic metrics entries.
    
    Args:
        subnet_id: Optional filter for a specific subnet
        limit: Maximum number of entries to return per subnet
        
    Returns:
        List of recent traffic metrics
    """
    query = select(SubnetTrafficMetrics).order_by(SubnetTrafficMetrics.timestamp.desc()).limit(limit)
    
    if subnet_id:
        query = query.filter(SubnetTrafficMetrics.subnet_id == subnet_id)
    
    result = await db.execute(query)
    metrics = result.scalars().all()
    
    return metrics
