"""
GrizzlySMS API Client - 100% Async
"""
import aiohttp
import logging
from typing import Optional, Dict, List, Tuple, Any
import json

from config import settings

logger = logging.getLogger(__name__)


class GrizzlyClient:
    """Async GrizzlySMS API Client"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = settings.GRIZZLY_API_URL
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request(self, params: Dict[str, Any]) -> Tuple[bool, Any]:
        """Make API request"""
        params['api_key'] = self.api_key
        
        try:
            session = await self._get_session()
            async with session.get(self.base_url, params=params) as resp:
                text = await resp.text()
                return self._parse_response(text)
        except aiohttp.ClientError as e:
            logger.error(f"API request error: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False, str(e)
    
    def _parse_response(self, text: str) -> Tuple[bool, Any]:
        """Parse API response"""
        # Error responses
        if text == "BAD_KEY":
            return False, "Invalid API key"
        if text == "NO_BALANCE":
            return False, "Insufficient balance"
        if text == "NO_NUMBERS":
            return False, "No numbers available"
        if text == "ERROR_SQL":
            return False, "Server error"
        if text == "BANNED":
            return False, "Account banned"
        if text == "BAD_STATUS":
            return False, "Invalid status"
        if text == "NO_ACTIVATION":
            return False, "Activation not found"
        if text == "WRONG_SERVICE":
            return False, "Wrong service"
        if text == "WRONG_COUNTRY":
            return False, "Wrong country"
        if text == "CANCELED":
            return False, "Canceled"
        
        # Success responses
        if text.startswith("ACCESS_BALANCE:"):
            try:
                balance = float(text.split(":")[1])
                return True, balance
            except (IndexError, ValueError):
                return False, "Invalid balance response"
        
        if text.startswith("ACCESS_NUMBER:"):
            try:
                parts = text.split(":")
                return True, {
                    "activation_id": parts[1],
                    "phone_number": parts[2]
                }
            except IndexError:
                return False, "Invalid activation response"
        
        if text == "STATUS_WAIT_CODE":
            return True, {"status": "waiting"}
        
        if text == "STATUS_WAIT_RETRY":
            return True, {"status": "waiting_retry"}
        
        if text == "STATUS_CANCEL":
            return True, {"status": "cancelled"}
        
        if text.startswith("STATUS_OK:"):
            try:
                code = text.split(":")[1]
                return True, {"status": "success", "code": code}
            except IndexError:
                return False, "Invalid status response"
        
        if text == "ACCESS_ACTIVATION":
            return True, {"status": "ready"}
        
        # Try JSON parse for prices
        try:
            data = json.loads(text)
            return True, data
        except:
            pass
        
        # Unknown response - treat as success
        return True, text
    
    # API Methods
    async def get_balance(self) -> Tuple[bool, Any]:
        """Get account balance"""
        return await self._request({"action": "getBalance"})
    
    async def buy_number(self, service: str, country: int, 
                         max_price: float = None) -> Tuple[bool, Any]:
        """Buy a phone number"""
        params = {
            "action": "getNumber",
            "service": service,
            "country": country
        }
        if max_price is not None and max_price > 0:
            params["maxPrice"] = max_price
        
        return await self._request(params)
    
    async def get_status(self, activation_id: str) -> Tuple[bool, Any]:
        """Get activation status"""
        return await self._request({
            "action": "getStatus",
            "id": activation_id
        })
    
    async def set_status(self, activation_id: str, status: int) -> Tuple[bool, Any]:
        """Set activation status
        
        Status codes:
        1 - SMS sent notification
        3 - request SMS again
        6 - cancel activation
        8 - activation completed
        """
        return await self._request({
            "action": "setStatus",
            "id": activation_id,
            "status": status
        })
    
    async def cancel_activation(self, activation_id: str) -> Tuple[bool, Any]:
        """Cancel activation"""
        return await self.set_status(activation_id, 6)
    
    async def resend_sms(self, activation_id: str) -> Tuple[bool, Any]:
        """Request SMS resend"""
        return await self.set_status(activation_id, 3)
    
    async def complete_activation(self, activation_id: str) -> Tuple[bool, Any]:
        """Complete activation"""
        return await self.set_status(activation_id, 8)
    
    async def get_prices(self, service: str = None, country: int = None) -> Tuple[bool, List[Dict]]:
        """Get prices and stock info"""
        params = {"action": "getPrices"}
        if service:
            params["service"] = service
        if country is not None:
            params["country"] = country
        
        success, result = await self._request(params)
        
        if not success:
            return False, result
        
        # Parse price data
        prices = []
        if isinstance(result, dict):
            for country_code, services in result.items():
                if isinstance(services, dict):
                    for svc, info in services.items():
                        if isinstance(info, dict):
                            prices.append({
                                "service": svc,
                                "country": int(country_code),
                                "price": info.get("price", 0),
                                "count": info.get("count", 0)
                            })
        elif isinstance(result, list):
            for item in result:
                if isinstance(item, dict):
                    prices.append(item)
        
        return True, prices
    
    async def check_availability(self, service: str, country: int) -> Tuple[bool, float, int]:
        """Check if number is available for service/country"""
        success, prices = await self.get_prices(service, country)
        
        if not success:
            return False, 0, 0
        
        for p in prices:
            if p.get("service") == service and p.get("country") == country:
                count = p.get("count", 0)
                price = p.get("price", 0)
                return count > 0, price, count
        
        return False, 0, 0


# Global client cache
_clients: Dict[str, GrizzlyClient] = {}


def get_client(api_key: str) -> GrizzlyClient:
    """Get or create client"""
    if api_key not in _clients:
        _clients[api_key] = GrizzlyClient(api_key)
    return _clients[api_key]


async def close_all_clients():
    """Close all clients"""
    for client in _clients.values():
        await client.close()
    _clients.clear()
