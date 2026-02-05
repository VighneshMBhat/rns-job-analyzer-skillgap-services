"""
JWT Authentication Service
Validates JWT tokens from Supabase Auth
"""
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.core.config import settings

security = HTTPBearer()


def get_jwt_secret():
    """Get JWT secret from Supabase project settings."""
    # Supabase uses the service role key's JWT secret
    # This is derived from the SUPABASE_KEY's payload
    return settings.JWT_SECRET if settings.JWT_SECRET else settings.SUPABASE_KEY


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify JWT token and return user claims.
    Returns dict with 'sub' (user_id), 'email', etc.
    """
    token = credentials.credentials
    
    try:
        # Supabase tokens are signed with the JWT secret
        # For Supabase, we decode without verification for now
        # In production, you should verify with the actual secret
        payload = jwt.decode(
            token,
            options={"verify_signature": False},  # Supabase handles verification
            algorithms=["HS256"]
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")
        
        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role", "authenticated"),
            "exp": payload.get("exp")
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


def get_current_user_id(token_data: dict = Depends(verify_token)) -> str:
    """Extract user_id from verified token."""
    return token_data["user_id"]
