from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

class LedgerEntryBase(BaseModel):
    account_id: str
    entry_type: str # DEBIT or CREDIT
    amount: Decimal

class TransactionCreate(BaseModel):
    reference_id: str
    transaction_type: str
    entries: List[LedgerEntryBase]
    metadata_json: Optional[str] = None

class TransactionResponse(BaseModel):
    id: str
    reference_id: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class RuleCondition(BaseModel):
    field: str
    operator: str # eq, gt, lt, contains
    value: str

class RuleAction(BaseModel):
    action_type: str # credit_reward
    params: dict

class Rule(BaseModel):
    id: str
    name: str
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    operator: str = "AND" # AND/OR for conditions
