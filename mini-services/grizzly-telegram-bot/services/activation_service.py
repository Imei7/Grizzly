"""
Activation service
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from database.db import db
from database.models import Activation
from api.grizzly_client import GrizzlySMSClient
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class ActivationService:
    """Service for activation operations"""
    
    @staticmethod
    async def buy_number(
        user_id: int,
        api_key: str,
        service: str,
        country: int,
        max_price: float = None
    ) -> tuple:
        """
        Buy a phone number for OTP
        Returns (success, activation/error_message)
        """
        # Check limit
        user = db.get_user_by_id(user_id)
        if not user:
            return False, "User not found"
        
        if user.otp_used >= user.otp_limit:
            return False, "OTP limit reached"
        
        client = GrizzlySMSClient(api_key)
        try:
            response = await client.get_number(
                service=service,
                country=country,
                max_price=max_price
            )
            
            if not response.success:
                return False, response.error
            
            # Create activation record
            activation = db.create_activation(
                user_id=user_id,
                activation_id=response.data["activation_id"],
                phone_number=response.data["phone_number"],
                service=service,
                country=country,
                price=0.0
            )
            
            # Increment user's OTP used count
            db.increment_otp_used(user_id)
            
            # Log
            db.create_log(
                action="buy_otp",
                details=f"Service: {service}, Country: {country}, Phone: {response.data['phone_number']}",
                user_id=user_id
            )
            
            logger.info(f"Bought number for user {user_id}: {response.data['phone_number']}")
            
            return True, activation
            
        finally:
            await client.close()
    
    @staticmethod
    async def check_status(api_key: str, activation_id: str) -> tuple:
        """
        Check activation status
        Returns (success, status_data/error_message)
        """
        client = GrizzlySMSClient(api_key)
        try:
            response = await client.get_status(activation_id)
            
            if not response.success:
                return False, response.error
            
            return True, response.data
            
        finally:
            await client.close()
    
    @staticmethod
    async def cancel_activation(api_key: str, activation_id: str, db_activation_id: int = None) -> tuple:
        """
        Cancel an activation
        Returns (success, message)
        """
        client = GrizzlySMSClient(api_key)
        try:
            response = await client.cancel_activation(activation_id)
            
            if response.success:
                # Update database
                if db_activation_id:
                    db.update_activation_status(db_activation_id, "cancelled")
                
                db.create_log(
                    action="cancel_activation",
                    details=f"Activation: {activation_id}",
                    user_id=None
                )
                
                logger.info(f"Cancelled activation {activation_id}")
                return True, "Activation cancelled"
            
            return False, response.error
            
        finally:
            await client.close()
    
    @staticmethod
    async def request_sms_again(api_key: str, activation_id: str) -> tuple:
        """
        Request SMS resend
        Returns (success, message)
        """
        client = GrizzlySMSClient(api_key)
        try:
            response = await client.request_sms_again(activation_id)
            
            if response.success:
                db.create_log(
                    action="request_sms_again",
                    details=f"Activation: {activation_id}",
                    user_id=None
                )
                
                logger.info(f"Requested SMS again for {activation_id}")
                return True, "SMS requested again"
            
            return False, response.error
            
        finally:
            await client.close()
    
    @staticmethod
    def get_user_activations(user_id: int, limit: int = 50) -> List[Activation]:
        """Get user's activations"""
        return db.get_user_activations(user_id, limit)
    
    @staticmethod
    def get_activation_by_id(activation_id: int) -> Optional[Activation]:
        """Get activation by database ID"""
        return db.get_activation_by_id(activation_id)
    
    @staticmethod
    def get_activation_by_grizzly_id(grizzly_id: str) -> Optional[Activation]:
        """Get activation by GrizzlySMS ID"""
        return db.get_activation_by_grizzly_id(grizzly_id)
    
    @staticmethod
    def update_status(activation_id: int, status: str, otp_code: str = None) -> bool:
        """Update activation status"""
        return db.update_activation_status(activation_id, status, otp_code)
    
    @staticmethod
    def get_waiting_activations() -> List[Activation]:
        """Get all waiting activations"""
        return db.get_waiting_activations()
    
    @staticmethod
    def format_activation_info(activation: Activation) -> str:
        """Format activation info for display"""
        service_info = settings.SERVICES.get(activation.service)
        country_info = settings.COUNTRIES.get(activation.country)
        
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else activation.service
        country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {activation.country}"
        
        status_info = {
            "waiting": ("⏳", "Waiting for SMS"),
            "success": ("✅", "Success"),
            "cancelled": ("❌", "Cancelled"),
            "expired": ("⌛", "Expired")
        }.get(activation.status, ("❓", "Unknown"))
        
        lines = [
            f"📱 Phone: {activation.phone_number}",
            f"🎯 Service: {service_name}",
            f"🌍 Country: {country_name}",
            f"📊 Status: {status_info[0]} {status_info[1]}",
        ]
        
        if activation.otp_code:
            lines.append(f"🔑 OTP Code: {activation.otp_code}")
        
        lines.append(f"🕐 Created: {activation.created_at.strftime('%d/%m/%Y %H:%M')}")
        
        return "\n".join(lines)


# Global activation service
activation_service = ActivationService()
