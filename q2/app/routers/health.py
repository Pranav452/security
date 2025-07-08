from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.schemas import HealthCheckResponse
from app.rate_limiting import get_redis_client
import sqlalchemy

router = APIRouter()

@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    database_status = "healthy"
    try:
        db.execute(sqlalchemy.text("SELECT 1"))
    except Exception as e:
        database_status = f"unhealthy: {str(e)}"
    
    redis_status = "healthy"
    try:
        redis_client = get_redis_client()
        if hasattr(redis_client, 'ping'):
            redis_client.ping()
        else:
            redis_status = "fallback: using in-memory rate limiting"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    overall_status = "healthy"
    if "unhealthy" in database_status or "unhealthy" in redis_status:
        overall_status = "unhealthy"
    elif "fallback" in redis_status:
        overall_status = "degraded"
    
    response = HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="2.0.0",
        database=database_status,
        redis=redis_status
    )
    
    if overall_status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.dict()
        )
    
    return response

@router.get("/health/database")
async def database_health(db: Session = Depends(get_db)):
    try:
        result = db.execute(sqlalchemy.text("SELECT 1")).fetchone()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "result": result[0] if result else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.utcnow(),
                "error": str(e)
            }
        )

@router.get("/health/redis")
async def redis_health():
    try:
        redis_client = get_redis_client()
        if hasattr(redis_client, 'ping'):
            redis_client.ping()
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow(),
                "type": "redis"
            }
        else:
            return {
                "status": "fallback",
                "timestamp": datetime.utcnow(),
                "type": "in-memory"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.utcnow(),
                "error": str(e)
            }
        ) 