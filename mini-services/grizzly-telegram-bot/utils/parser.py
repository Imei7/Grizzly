"""
Response parser utility
"""
from typing import Optional, Dict, Any, List
import json


def parse_balance_response(response: str) -> Optional[float]:
    """
    Parse balance response
    ACCESS_BALANCE:10.50 -> 10.50
    """
    if response.startswith("ACCESS_BALANCE:"):
        try:
            return float(response.split(":")[1])
        except (IndexError, ValueError):
            return None
    return None


def parse_activation_response(response: str) -> Optional[Dict[str, str]]:
    """
    Parse activation response
    ACCESS_NUMBER:934857345:628123456789 -> {activation_id: '934857345', phone_number: '628123456789'}
    """
    if response.startswith("ACCESS_NUMBER:"):
        try:
            parts = response.split(":")
            return {
                "activation_id": parts[1],
                "phone_number": parts[2]
            }
        except IndexError:
            return None
    return None


def parse_status_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Parse status response
    STATUS_WAIT_CODE -> {status: 'waiting'}
    STATUS_OK:123456 -> {status: 'success', code: '123456'}
    STATUS_CANCEL -> {status: 'cancelled'}
    """
    if response == "STATUS_WAIT_CODE":
        return {"status": "waiting"}
    elif response.startswith("STATUS_OK:"):
        try:
            code = response.split(":")[1]
            return {"status": "success", "code": code}
        except IndexError:
            return None
    elif response == "STATUS_CANCEL":
        return {"status": "cancelled"}
    return None


def parse_prices_response(response: Any) -> List[Dict[str, Any]]:
    """
    Parse prices response
    Returns list of {service, country, price, count}
    """
    result = []
    
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return result
    
    if isinstance(response, dict):
        # Format: {country: {service: {price, count}}}
        for country, services in response.items():
            if isinstance(services, dict):
                for service, info in services.items():
                    if isinstance(info, dict):
                        result.append({
                            "country": int(country),
                            "service": service,
                            "price": info.get("price", 0),
                            "count": info.get("count", 0)
                        })
    
    elif isinstance(response, list):
        for item in response:
            if isinstance(item, dict):
                result.append({
                    "country": item.get("country", 0),
                    "service": item.get("service", ""),
                    "price": item.get("price", 0),
                    "count": item.get("count", 0)
                })
    
    return result


def format_phone_number(phone: str) -> str:
    """
    Format phone number for display
    """
    if not phone:
        return ""
    
    # Remove any non-digit characters
    phone = ''.join(c for c in phone if c.isdigit())
    
    # Add + prefix if not present
    if not phone.startswith("+"):
        phone = "+" + phone
    
    return phone


def mask_api_key(api_key: str) -> str:
    """
    Mask API key for display
    abc123xyz -> abc***xyz
    """
    if not api_key or len(api_key) < 6:
        return "***"
    
    return f"{api_key[:3]}...{api_key[-3:]}"


def format_price(price: float, currency: str = "₽") -> str:
    """
    Format price for display
    """
    if price == 0:
        return "Free"
    return f"{price:.2f} {currency}"


def format_timestamp(dt) -> str:
    """
    Format datetime for display
    """
    if not dt:
        return ""
    
    if isinstance(dt, str):
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    
    return dt.strftime("%d/%m/%Y %H:%M")
