"""
Database models for GrizzlySMS Telegram Bot
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum


class UserStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ActivationStatus(Enum):
    WAITING = "waiting"
    SUCCESS = "success"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class User:
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    api_key: str
    status: str  # pending, approved, rejected
    otp_limit: int
    otp_used: int
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_row(cls, row: tuple) -> 'User':
        return cls(
            id=row[0],
            telegram_id=row[1],
            username=row[2],
            first_name=row[3],
            last_name=row[4],
            api_key=row[5],
            status=row[6],
            otp_limit=row[7],
            otp_used=row[8],
            created_at=datetime.fromisoformat(row[9]) if isinstance(row[9], str) else row[9],
            updated_at=datetime.fromisoformat(row[10]) if isinstance(row[10], str) else row[10],
        )


@dataclass
class Activation:
    id: int
    user_id: int
    activation_id: str  # GrizzlySMS activation ID
    phone_number: str
    service: str
    country: int
    price: float
    status: str
    otp_code: Optional[str]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    
    @classmethod
    def from_row(cls, row: tuple) -> 'Activation':
        return cls(
            id=row[0],
            user_id=row[1],
            activation_id=row[2],
            phone_number=row[3],
            service=row[4],
            country=row[5],
            price=row[6],
            status=row[7],
            otp_code=row[8],
            created_at=datetime.fromisoformat(row[9]) if isinstance(row[9], str) else row[9],
            updated_at=datetime.fromisoformat(row[10]) if isinstance(row[10], str) else row[10],
            expires_at=datetime.fromisoformat(row[11]) if row[11] and isinstance(row[11], str) else row[11],
        )


@dataclass
class BuyTask:
    id: int
    user_id: int
    service: str
    country: int
    max_price: float
    status: str
    activation_id: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    
    @classmethod
    def from_row(cls, row: tuple) -> 'BuyTask':
        return cls(
            id=row[0],
            user_id=row[1],
            service=row[2],
            country=row[3],
            max_price=row[4],
            status=row[5],
            activation_id=row[6],
            created_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
            completed_at=datetime.fromisoformat(row[8]) if row[8] and isinstance(row[8], str) else row[8],
        )


@dataclass
class SniperTask:
    id: int
    user_id: int
    service: str
    country: int
    max_price: float
    status: str  # active, paused, completed, cancelled
    activation_id: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    
    @classmethod
    def from_row(cls, row: tuple) -> 'SniperTask':
        return cls(
            id=row[0],
            user_id=row[1],
            service=row[2],
            country=row[3],
            max_price=row[4],
            status=row[5],
            activation_id=row[6],
            created_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
            completed_at=datetime.fromisoformat(row[8]) if row[8] and isinstance(row[8], str) else row[8],
        )


@dataclass
class AutoBuyTask:
    id: int
    user_id: int
    service: str
    country: int
    max_price: float
    max_count: int  # 0 = unlimited
    current_count: int
    status: str  # active, paused, completed, cancelled
    created_at: datetime
    completed_at: Optional[datetime]
    
    @classmethod
    def from_row(cls, row: tuple) -> 'AutoBuyTask':
        return cls(
            id=row[0],
            user_id=row[1],
            service=row[2],
            country=row[3],
            max_price=row[4],
            max_count=row[5],
            current_count=row[6],
            status=row[7],
            created_at=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8],
            completed_at=datetime.fromisoformat(row[9]) if row[9] and isinstance(row[9], str) else row[9],
        )


@dataclass
class Log:
    id: int
    user_id: Optional[int]
    action: str
    details: str
    created_at: datetime
    
    @classmethod
    def from_row(cls, row: tuple) -> 'Log':
        return cls(
            id=row[0],
            user_id=row[1],
            action=row[2],
            details=row[3],
            created_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
        )
