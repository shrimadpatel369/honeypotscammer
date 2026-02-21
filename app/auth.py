from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import settings
import logging

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="x-api-key", auto_error=True)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Verify API key from request header
    
    Args:
        api_key: API key from x-api-key header
        
    Raises:
        HTTPException: If API key is invalid
        
    Returns:
        str: Validated API key
    """
    logger.info(f"🔑 AUTH CHECK - Received API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")
    logger.info(f"Expected API Key: {settings.api_key[:10]}...{settings.api_key[-4:] if len(settings.api_key) > 14 else ''}")
    
    if api_key != settings.api_key:
        logger.error(f"❌ AUTH FAILED - Invalid API key provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    logger.info(f"✅ AUTH SUCCESS - API key validated")
    return api_key