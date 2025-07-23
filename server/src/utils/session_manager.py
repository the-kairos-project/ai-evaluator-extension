"""Session management for the MCP Server."""

from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
import json
import uuid
from src.utils.logging import get_structured_logger
import redis.asyncio as redis
from pydantic import BaseModel, Field

from src.config.settings import settings

logger = get_structured_logger(__name__)


class Session(BaseModel):
    """Session model."""
    
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    data: Dict[str, Any] = Field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            data=data.get("data", {})
        )


class SessionManager:
    """Manages user sessions with Redis backend."""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 3600,
        key_prefix: str = "mcp:session:"
    ) -> None:
        """Initialize the session manager.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default session TTL in seconds
            key_prefix: Prefix for Redis keys
        """
        self.redis_url = redis_url or settings.redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._redis: Optional[redis.Redis] = None
        self._in_memory_store: Dict[str, Session] = {}
        self._use_redis = bool(self.redis_url)
    
    async def initialize(self) -> None:
        """Initialize the session manager."""
        if self._use_redis:
            try:
                self._redis = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self._redis.ping()
                logger.info("Redis session store initialized")
            except Exception as e:
                logger.warning(
                    "Failed to connect to Redis, falling back to in-memory store",
                    error=str(e)
                )
                self._use_redis = False
                self._redis = None
        else:
            logger.info("Using in-memory session store")
    
    async def create_session(
        self,
        user_id: str,
        data: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> Session:
        """Create a new session.
        
        Args:
            user_id: User ID for the session
            data: Initial session data
            ttl: Session TTL in seconds
            
        Returns:
            Session: The created session
        """
        ttl = ttl or self.default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        session = Session(
            user_id=user_id,
            expires_at=expires_at,
            data=data or {}
        )
        
        await self._store_session(session, ttl)
        
        logger.info(
            "Session created",
            session_id=session.session_id,
            user_id=user_id,
            expires_in=ttl
        )
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Optional[Session]: The session if found and not expired
        """
        if self._use_redis and self._redis:
            try:
                data = await self._redis.get(f"{self.key_prefix}{session_id}")
                if data:
                    session_data = json.loads(data)
                    session = Session.from_dict(session_data)
                    
                    if session.is_expired():
                        await self.delete_session(session_id)
                        return None
                    
                    return session
            except Exception as e:
                logger.error("Failed to get session from Redis", error=str(e))
        else:
            # In-memory fallback
            session = self._in_memory_store.get(session_id)
            if session and session.is_expired():
                del self._in_memory_store[session_id]
                return None
            return session
        
        return None
    
    async def update_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        extend_ttl: bool = True
    ) -> Optional[Session]:
        """Update session data.
        
        Args:
            session_id: Session ID
            data: Data to update
            extend_ttl: Whether to extend the session TTL
            
        Returns:
            Optional[Session]: Updated session if found
        """
        session = await self.get_session(session_id)
        if not session:
            return None
        
        session.data.update(data)
        
        if extend_ttl:
            session.expires_at = datetime.utcnow() + timedelta(seconds=self.default_ttl)
        
        ttl = int((session.expires_at - datetime.utcnow()).total_seconds())
        await self._store_session(session, ttl)
        
        logger.info("Session updated", session_id=session_id)
        return session
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        if self._use_redis and self._redis:
            try:
                result = await self._redis.delete(f"{self.key_prefix}{session_id}")
                logger.info("Session deleted", session_id=session_id)
                return bool(result)
            except Exception as e:
                logger.error("Failed to delete session from Redis", error=str(e))
        else:
            if session_id in self._in_memory_store:
                del self._in_memory_store[session_id]
                logger.info("Session deleted", session_id=session_id)
                return True
        
        return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.
        
        Returns:
            int: Number of sessions cleaned up
        """
        cleaned = 0
        
        if self._use_redis and self._redis:
            # Redis handles expiration automatically
            logger.info("Redis handles session expiration automatically")
        else:
            # Clean up in-memory store
            expired_ids = [
                sid for sid, session in self._in_memory_store.items()
                if session.is_expired()
            ]
            
            for sid in expired_ids:
                del self._in_memory_store[sid]
                cleaned += 1
            
            if cleaned > 0:
                logger.info("Cleaned up expired sessions", count=cleaned)
        
        return cleaned
    
    async def _store_session(self, session: Session, ttl: int) -> None:
        """Store a session.
        
        Args:
            session: Session to store
            ttl: TTL in seconds
        """
        if self._use_redis and self._redis:
            try:
                await self._redis.setex(
                    f"{self.key_prefix}{session.session_id}",
                    ttl,
                    json.dumps(session.to_dict())
                )
            except Exception as e:
                logger.error("Failed to store session in Redis", error=str(e))
                # Fallback to in-memory
                self._in_memory_store[session.session_id] = session
        else:
            self._in_memory_store[session.session_id] = session
    
    async def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List[Session]: List of active sessions
        """
        sessions = []
        
        if self._use_redis and self._redis:
            try:
                # Scan for all session keys
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(
                        cursor,
                        match=f"{self.key_prefix}*",
                        count=100
                    )
                    
                    for key in keys:
                        data = await self._redis.get(key)
                        if data:
                            session_data = json.loads(data)
                            if session_data.get("user_id") == user_id:
                                session = Session.from_dict(session_data)
                                if not session.is_expired():
                                    sessions.append(session)
                    
                    if cursor == 0:
                        break
            except Exception as e:
                logger.error("Failed to get user sessions from Redis", error=str(e))
        else:
            # In-memory fallback
            sessions = [
                session for session in self._in_memory_store.values()
                if session.user_id == user_id and not session.is_expired()
            ]
        
        return sessions
    
    async def shutdown(self) -> None:
        """Shutdown the session manager."""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed") 