from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, DECIMAL
from sqlalchemy.orm import relationship
import enum
import datetime
from .database import Base

class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"

class TransactionType(str, enum.Enum):
    REWARD_CREDIT = "REWARD_CREDIT"
    REWARD_REVERSAL = "REWARD_REVERSAL"
    PAYOUT = "PAYOUT"

class EntryType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(String, primary_key=True, index=True) # e.g., "user_123" or "system_rewards"
    name = Column(String)
    # We can cache balance here, but true balance is sum of ledger entries
    current_balance = Column(DECIMAL(20, 2), default=0.0)

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True) # UUID
    reference_id = Column(String, unique=True, index=True) # Idempotency key / External ID
    transaction_type = Column(String) # REWARD_CREDIT, etc.
    status = Column(String, default=TransactionStatus.PENDING)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    metadata_json = Column(String, nullable=True) # Store extra info like 'reason'
    
    entries = relationship("LedgerEntry", back_populates="transaction")

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, ForeignKey("transactions.id"))
    account_id = Column(String, ForeignKey("accounts.id"))
    entry_type = Column(String) # DEBIT or CREDIT
    amount = Column(DECIMAL(20, 2))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    transaction = relationship("Transaction", back_populates="entries")
    account = relationship("Account")
