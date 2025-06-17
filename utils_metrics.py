import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from models import Subnet, SubnetTrafficMetrics
from vyos_core import collect_subnet_traffic_metrics
from config import get_async_db

async def collect_metrics_task():
    """
    Background task that collects subnet traffic metrics at regular intervals.
    """
    while True:
        try:
            # Collect metrics from VyOS
            metrics = await collect_subnet_traffic_metrics()
            
            # Get a database session
            db = await get_async_db().__anext__()
            
            # Store metrics in the database
            for metric in metrics:
                db_metric = SubnetTrafficMetrics(
                    subnet_id=metric["subnet_id"],
                    timestamp=datetime.utcnow(),
                    rx_bytes=metric["rx_bytes"],
                    tx_bytes=metric["tx_bytes"],
                    rx_packets=metric["rx_packets"],
                    tx_packets=metric["tx_packets"],
                    active_hosts=metric["active_hosts"]
                )
                db.add(db_metric)
            
            await db.commit()
            print(f"Collected traffic metrics for {len(metrics)} subnets at {datetime.utcnow().isoformat()}")
            
        except Exception as e:
            print(f"Error in metrics collection task: {e}")
        
        # Wait for 5 minutes before collecting again
        await asyncio.sleep(300)  # 5 minutes

async def cleanup_old_metrics_task():
    """
    Background task that removes old metrics data to prevent database bloat.
    Runs daily and removes data older than 90 days.
    """
    while True:
        try:
            # Get a database session
            db = await get_async_db().__anext__()
            
            # Delete metrics older than 90 days
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            # Delete query
            delete_stmt = SubnetTrafficMetrics.__table__.delete().where(
                SubnetTrafficMetrics.timestamp < cutoff_date
            )
            
            await db.execute(delete_stmt)
            await db.commit()
            
            print(f"Cleaned up old metrics data older than {cutoff_date.isoformat()}")
            
        except Exception as e:
            print(f"Error in metrics cleanup task: {e}")
        
        # Run once a day
        await asyncio.sleep(86400)  # 24 hours

def start_metrics_tasks():
    """
    Start the background tasks for metrics collection and cleanup.
    Call this function when your application starts.
    """
    loop = asyncio.get_event_loop()
    loop.create_task(collect_metrics_task())
    loop.create_task(cleanup_old_metrics_task())
    print("Started background tasks for subnet traffic metrics collection and cleanup")