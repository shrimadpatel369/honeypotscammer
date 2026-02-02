from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import settings

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
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
