"""Pydantic models for API request/response types."""
from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_at: str


class Position(BaseModel):
    ticket: int
    symbol: str
    direction: str
    volume: float
    open_price: float
    current_price: float
    sl: float
    tp: float
    profit: float
    swap: float
    open_time: str


class AccountInfo(BaseModel):
    balance: float
    equity: float
    margin: float
    free_margin: float
    daily_pnl: float


class Trade(BaseModel):
    ticket: int
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    profit: float
    open_time: str
    close_time: str
    duration: str
    regime: Optional[str] = None


class Decision(BaseModel):
    timestamp: str
    symbol: str
    timeframe: str
    regime: str
    confidence: float
    sl_pips: float
    tp_pips: float
    lot_size: float
    reasoning: str


class EquityPoint(BaseModel):
    time: str
    value: float


class DrawdownPoint(BaseModel):
    time: str
    value: float


class Alert(BaseModel):
    id: int
    type: str
    message: str
    severity: str
    acknowledged: bool
    created_at: str


class StrategyConfig(BaseModel):
    config: dict
