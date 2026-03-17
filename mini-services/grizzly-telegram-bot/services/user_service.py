"""
User service
"""
from typing import Optional, List
from datetime import datetime

from database.db import db
from database.models import User
from api.grizzly_client import GrizzlySMSClient
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class UserService:
    """Service for user operations"""
    
    @staticmethod
    async def register_user(
        telegram_id: int,
        api_key: str,
        username: str = None,
        first_name: str = None,
        last_name: str = None
    ) -> User:
        """Register a new user"""
        # Check if user already exists
        existing = db.get_user_by_telegram_id(telegram_id)
        if existing:
            # Update API key if different
            if existing.api_key != api_key:
                db.update_user_api_key(existing.id, api_key)
                logger.info(f"Updated API key for user {telegram_id}")
            return existing
        
        # Create new user
        user = db.create_user(
            telegram_id=telegram_id,
            api_key=api_key,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        
        logger.info(f"Registered new user {telegram_id}")
        return user
    
    @staticmethod
    def get_user(telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        return db.get_user_by_telegram_id(telegram_id)
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by database ID"""
        return db.get_user_by_id(user_id)
    
    @staticmethod
    def approve_user(user_id: int) -> bool:
        """Approve a user"""
        result = db.update_user_status(user_id, "approved")
        if result:
            logger.info(f"Approved user {user_id}")
        return result
    
    @staticmethod
    def reject_user(user_id: int) -> bool:
        """Reject a user"""
        result = db.update_user_status(user_id, "rejected")
        if result:
            logger.info(f"Rejected user {user_id}")
        return result
    
    @staticmethod
    def is_approved(telegram_id: int) -> bool:
        """Check if user is approved"""
        user = db.get_user_by_telegram_id(telegram_id)
        return user and user.status == "approved"
    
    @staticmethod
    def is_registered(telegram_id: int) -> bool:
        """Check if user is registered"""
        return db.get_user_by_telegram_id(telegram_id) is not None
    
    @staticmethod
    def get_all_users() -> List[User]:
        """Get all users"""
        return db.get_all_users()
    
    @staticmethod
    def get_pending_users() -> List[User]:
        """Get pending users"""
        return db.get_pending_users()
    
    @staticmethod
    def get_approved_users() -> List[User]:
        """Get approved users"""
        return db.get_approved_users()
    
    @staticmethod
    def update_api_key(user_id: int, api_key: str) -> bool:
        """Update user API key"""
        result = db.update_user_api_key(user_id, api_key)
        if result:
            logger.info(f"Updated API key for user {user_id}")
        return result
    
    @staticmethod
    def set_otp_limit(user_id: int, limit: int) -> bool:
        """Set OTP limit for user"""
        result = db.update_user_otp_limit(user_id, limit)
        if result:
            logger.info(f"Set OTP limit {limit} for user {user_id}")
        return result
    
    @staticmethod
    def check_otp_limit(user_id: int) -> bool:
        """Check if user has remaining OTP limit"""
        user = db.get_user_by_id(user_id)
        if not user:
            return False
        return user.otp_used < user.otp_limit
    
    @staticmethod
    def get_remaining_otp(user_id: int) -> int:
        """Get remaining OTP count for user"""
        user = db.get_user_by_id(user_id)
        if not user:
            return 0
        return max(0, user.otp_limit - user.otp_used)
    
    @staticmethod
    async def verify_api_key(api_key: str) -> tuple:
        """Verify API key by checking balance"""
        client = GrizzlySMSClient(api_key)
        try:
            response = await client.get_balance()
            return response.success, response.data.get("balance", 0) if response.success else response.error
        finally:
            await client.close()
    
    @staticmethod
    async def get_balance(user_id: int) -> tuple:
        """Get user's GrizzlySMS balance"""
        user = db.get_user_by_id(user_id)
        if not user:
            return False, "User not found"
        
        client = GrizzlySMSClient(user.api_key)
        try:
            response = await client.get_balance()
            if response.success:
                return True, response.data.get("balance", 0)
            return False, response.error
        finally:
            await client.close()
    
    @staticmethod
    def is_admin(telegram_id: int) -> bool:
        """Check if user is admin"""
        return telegram_id in settings.ADMIN_IDS
    
    @staticmethod
    def get_user_stats(user_id: int) -> dict:
        """Get user statistics"""
        user = db.get_user_by_id(user_id)
        if not user:
            return {}
        
        activations = db.get_user_activations(user_id, limit=1000)
        
        total = len(activations)
        successful = sum(1 for a in activations if a.status == "success")
        cancelled = sum(1 for a in activations if a.status == "cancelled")
        waiting = sum(1 for a in activations if a.status == "waiting")
        
        return {
            "total_activations": total,
            "successful": successful,
            "cancelled": cancelled,
            "waiting": waiting,
            "otp_used": user.otp_used,
            "otp_limit": user.otp_limit,
            "remaining": user.otp_limit - user.otp_used
        }


# Global user service
user_service = UserService()
