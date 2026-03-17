"""
GrizzlySMS API Client
"""
import aiohttp
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import json

from config.settings import settings


@dataclass
class APIResponse:
    success: bool
    data: Any
    error: Optional[str] = None
    raw_response: Optional[str] = None


class GrizzlySMSClient:
    """
    Async client for GrizzlySMS API
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = settings.GRIZZLY_API_BASE_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request(self, params: Dict[str, Any]) -> APIResponse:
        """
        Make API request
        """
        params['api_key'] = self.api_key
        
        try:
            session = await self._get_session()
            async with session.get(self.base_url, params=params) as response:
                text = await response.text()
                
                # Check for common error responses
                if text == "BAD_KEY":
                    return APIResponse(False, None, "Invalid API key", text)
                elif text == "NO_BALANCE":
                    return APIResponse(False, None, "Insufficient balance", text)
                elif text == "NO_NUMBERS":
                    return APIResponse(False, None, "No numbers available", text)
                elif text == "ERROR_SQL":
                    return APIResponse(False, None, "Server error", text)
                elif text == "BANNED":
                    return APIResponse(False, None, "Account banned", text)
                elif text.startswith("ACCESS_NUMBER:"):
                    # Parse activation response
                    parts = text.split(":")
                    if len(parts) >= 3:
                        return APIResponse(
                            True,
                            {
                                "activation_id": parts[1],
                                "phone_number": parts[2]
                            },
                            None,
                            text
                        )
                    return APIResponse(False, None, "Invalid response format", text)
                elif text.startswith("ACCESS_BALANCE:"):
                    balance = text.split(":")[1]
                    return APIResponse(True, {"balance": float(balance)}, None, text)
                elif text.startswith("STATUS_WAIT_CODE"):
                    return APIResponse(True, {"status": "waiting"}, None, text)
                elif text.startswith("STATUS_OK:"):
                    code = text.split(":")[1]
                    return APIResponse(True, {"status": "success", "code": code}, None, text)
                elif text == "STATUS_CANCEL":
                    return APIResponse(True, {"status": "cancelled"}, None, text)
                elif text.startswith("ACCESS_ACTIVATION"):
                    return APIResponse(True, {"status": "activation_ready"}, None, text)
                elif text == "BAD_STATUS":
                    return APIResponse(False, None, "Invalid status", text)
                elif text == "NO_ACTIVATION":
                    return APIResponse(False, None, "Activation not found", text)
                else:
                    # Try to parse as JSON
                    try:
                        data = json.loads(text)
                        return APIResponse(True, data, None, text)
                    except json.JSONDecodeError:
                        return APIResponse(True, text, None, text)
                        
        except aiohttp.ClientError as e:
            return APIResponse(False, None, f"Network error: {str(e)}", None)
        except asyncio.TimeoutError:
            return APIResponse(False, None, "Request timeout", None)
        except Exception as e:
            return APIResponse(False, None, f"Unexpected error: {str(e)}", None)
    
    async def get_balance(self) -> APIResponse:
        """
        Get account balance
        action=getBalance
        """
        return await self._request({"action": "getBalance"})
    
    async def get_number(self, service: str, country: int, max_price: float = None) -> APIResponse:
        """
        Purchase a phone number for OTP
        action=getNumber
        
        Args:
            service: Service code (e.g., 'wa' for WhatsApp)
            country: Country code (integer)
            max_price: Maximum price willing to pay
        """
        params = {
            "action": "getNumber",
            "service": service,
            "country": country
        }
        if max_price is not None:
            params["maxPrice"] = max_price
        
        return await self._request(params)
    
    async def get_status(self, activation_id: str) -> APIResponse:
        """
        Check OTP status
        action=getStatus
        
        Args:
            activation_id: The activation ID from getNumber
        """
        return await self._request({
            "action": "getStatus",
            "id": activation_id
        })
    
    async def set_status(self, activation_id: str, status: int) -> APIResponse:
        """
        Change activation status
        action=setStatus
        
        Status codes:
        1 - ready (notify that SMS was sent)
        3 - request new SMS
        6 - cancel activation
        
        Args:
            activation_id: The activation ID
            status: Status code (1, 3, or 6)
        """
        return await self._request({
            "action": "setStatus",
            "id": activation_id,
            "status": status
        })
    
    async def get_prices(self, service: str = None, country: int = None) -> APIResponse:
        """
        Get prices and stock
        action=getPrices
        
        Args:
            service: Optional service code to filter
            country: Optional country code to filter
        """
        params = {"action": "getPrices"}
        if service:
            params["service"] = service
        if country is not None:
            params["country"] = country
        
        return await self._request(params)
    
    async def cancel_activation(self, activation_id: str) -> APIResponse:
        """
        Cancel an activation
        """
        return await self.set_status(activation_id, 6)
    
    async def request_sms_again(self, activation_id: str) -> APIResponse:
        """
        Request SMS resend
        """
        return await self.set_status(activation_id, 3)
    
    async def notify_sms_sent(self, activation_id: str) -> APIResponse:
        """
        Notify that SMS was sent (mark as ready)
        """
        return await self.set_status(activation_id, 1)


class GrizzlySMSClientFactory:
    """
    Factory for creating GrizzlySMS clients
    """
    
    _instances: Dict[str, GrizzlySMSClient] = {}
    
    @classmethod
    def get_client(cls, api_key: str) -> GrizzlySMSClient:
        if api_key not in cls._instances:
            cls._instances[api_key] = GrizzlySMSClient(api_key)
        return cls._instances[api_key]
    
    @classmethod
    async def close_all(cls):
        for client in cls._instances.values():
            await client.close()
        cls._instances.clear()
