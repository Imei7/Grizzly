"""
Price service
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from api.grizzly_client import GrizzlySMSClient
from config.settings import settings
from utils.logger import get_logger
from utils.parser import parse_prices_response

logger = get_logger(__name__)


class PriceService:
    """Service for price and stock operations"""
    
    _cache: Dict[str, Any] = {}
    _cache_time: Dict[str, datetime] = {}
    _cache_duration: int = 60  # seconds
    
    @staticmethod
    async def get_prices(
        api_key: str = None,
        service: str = None,
        country: int = None,
        use_cache: bool = True
    ) -> tuple:
        """
        Get prices and stock info
        Returns (success, prices_list/error_message)
        """
        cache_key = f"prices_{service}_{country}"
        
        # Check cache
        if use_cache and cache_key in PriceService._cache:
            cache_time = PriceService._cache_time.get(cache_key)
            if cache_time and (datetime.now() - cache_time).total_seconds() < PriceService._cache_duration:
                return True, PriceService._cache[cache_key]
        
        # Make API request
        if api_key:
            client = GrizzlySMSClient(api_key)
        else:
            # Use a default client without API key (some endpoints don't require it)
            client = GrizzlySMSClient("")
        
        try:
            response = await client.get_prices(service=service, country=country)
            
            if not response.success:
                return False, response.error
            
            # Parse response
            prices = parse_prices_response(response.data)
            
            # Filter results
            if service:
                prices = [p for p in prices if p["service"] == service]
            if country is not None:
                prices = [p for p in prices if p["country"] == country]
            
            # Sort by price
            prices.sort(key=lambda x: x.get("price", 0))
            
            # Cache results
            PriceService._cache[cache_key] = prices
            PriceService._cache_time[cache_key] = datetime.now()
            
            return True, prices
            
        finally:
            await client.close()
    
    @staticmethod
    async def get_service_prices(api_key: str, service: str) -> tuple:
        """Get prices for a specific service"""
        return await PriceService.get_prices(api_key, service=service)
    
    @staticmethod
    async def get_country_prices(api_key: str, country: int) -> tuple:
        """Get prices for a specific country"""
        return await PriceService.get_prices(api_key, country=country)
    
    @staticmethod
    async def check_availability(
        api_key: str,
        service: str,
        country: int,
        max_price: float = None
    ) -> tuple:
        """
        Check if a number is available for service/country
        Returns (available, price, count)
        """
        success, result = await PriceService.get_prices(
            api_key,
            service=service,
            country=country,
            use_cache=False
        )
        
        if not success:
            return False, 0, 0
        
        for item in result:
            if item["service"] == service and item["country"] == country:
                count = item.get("count", 0)
                price = item.get("price", 0)
                
                if count > 0:
                    if max_price is None or price <= max_price:
                        return True, price, count
                
                return False, price, count
        
        return False, 0, 0
    
    @staticmethod
    async def get_all_available(api_key: str = None) -> List[Dict]:
        """Get all available services with stock"""
        success, prices = await PriceService.get_prices(api_key)
        
        if not success:
            return []
        
        # Filter only available
        available = [p for p in prices if p.get("count", 0) > 0]
        
        # Group by service
        grouped = {}
        for item in available:
            service = item["service"]
            if service not in grouped:
                grouped[service] = []
            grouped[service].append(item)
        
        return grouped
    
    @staticmethod
    def format_price_info(price_data: Dict) -> str:
        """Format price info for display"""
        service_info = settings.SERVICES.get(price_data.get("service"))
        country_info = settings.COUNTRIES.get(price_data.get("country"))
        
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else price_data.get("service", "Unknown")
        country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {price_data.get('country')}"
        
        price = price_data.get("price", 0)
        count = price_data.get("count", 0)
        
        stock_emoji = "🟢" if count > 10 else "🟡" if count > 0 else "🔴"
        stock_text = f"{count} available" if count > 0 else "Out of stock"
        
        return f"{service_name} - {country_name}\n💰 Price: {price:.2f}₽\n📦 Stock: {stock_emoji} {stock_text}"
    
    @staticmethod
    def clear_cache():
        """Clear price cache"""
        PriceService._cache.clear()
        PriceService._cache_time.clear()
    
    @staticmethod
    async def monitor_stock(
        api_key: str,
        service: str,
        country: int,
        callback,
        interval: float = 3.0,
        max_price: float = None
    ):
        """
        Monitor stock and call callback when available
        """
        while True:
            available, price, count = await PriceService.check_availability(
                api_key, service, country, max_price
            )
            
            if available:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(True, price, count)
                    else:
                        callback(True, price, count)
                    break
                except Exception as e:
                    logger.error(f"Stock monitor callback error: {e}")
            
            await asyncio.sleep(interval)


# Global price service
price_service = PriceService()
