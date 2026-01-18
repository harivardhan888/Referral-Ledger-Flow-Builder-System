import uuid
from sqlalchemy.orm import Session
from . import models, schemas
from decimal import Decimal
import json

SYSTEM_ACCOUNT_ID = "system_rewards_pool"

def get_or_create_account(db: Session, account_id: str):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        account = models.Account(id=account_id, name=f"Account {account_id}")
        db.add(account)
        db.commit()
        db.refresh(account)
    return account

def process_reward_credit(db: Session, user_id: str, amount: Decimal, reference_id: str, description: str = "Reward"):
    # 1. Idempotency Check
    existing_tx = db.query(models.Transaction).filter(models.Transaction.reference_id == reference_id).first()
    if existing_tx:
        return existing_tx

    # 2. Create Transaction Record
    tx_id = str(uuid.uuid4())
    transaction = models.Transaction(
        id=tx_id,
        reference_id=reference_id,
        transaction_type=models.TransactionType.REWARD_CREDIT,
        status=models.TransactionStatus.COMPLETED,
        metadata_json=json.dumps({"description": description})
    )
    db.add(transaction)

    # 3. Create Ledger Entries (Double Entry)
    # Credit User, Debit System
    
    # Ensure accounts exist
    get_or_create_account(db, user_id)
    get_or_create_account(db, SYSTEM_ACCOUNT_ID)

    # Entry 1: Credit User
    entry_credit = models.LedgerEntry(
        transaction_id=tx_id,
        account_id=user_id,
        entry_type=models.EntryType.CREDIT,
        amount=amount
    )
    
    # Entry 2: Debit System
    entry_debit = models.LedgerEntry(
        transaction_id=tx_id,
        account_id=SYSTEM_ACCOUNT_ID,
        entry_type=models.EntryType.DEBIT,
        amount=amount
    )
    
    db.add(entry_credit)
    db.add(entry_debit)
    
    # 4. Update Balances (Denormalized)
    user_account = db.query(models.Account).filter(models.Account.id == user_id).first()
    system_account = db.query(models.Account).filter(models.Account.id == SYSTEM_ACCOUNT_ID).first()
    
    user_account.current_balance += amount
    system_account.current_balance -= amount
    
    db.commit()
    db.refresh(transaction)
    return transaction

def reverse_reward(db: Session, original_reference_id: str, reason: str = "Administrative Reversal"):
    # Find original transaction
    original_tx = db.query(models.Transaction).filter(models.Transaction.reference_id == original_reference_id).first()
    if not original_tx:
        raise ValueError("Original transaction not found")
    
    if original_tx.status == models.TransactionStatus.REVERSED:
        return original_tx # Already reversed

    # Create Reversal Transaction
    reversal_ref_id = f"reversal_{original_reference_id}"
    existing_rev = db.query(models.Transaction).filter(models.Transaction.reference_id == reversal_ref_id).first()
    if existing_rev:
        return existing_rev

    tx_id = str(uuid.uuid4())
    transaction = models.Transaction(
        id=tx_id,
        reference_id=reversal_ref_id,
        transaction_type=models.TransactionType.REWARD_REVERSAL,
        status=models.TransactionStatus.COMPLETED,
        metadata_json=json.dumps({"original_tx_id": original_tx.id, "reason": reason})
    )
    db.add(transaction)

    # Calculate amount from original entries
    # Find the credit to the user in the original transaction
    original_credit_entry = db.query(models.LedgerEntry).filter(
        models.LedgerEntry.transaction_id == original_tx.id,
        models.LedgerEntry.entry_type == models.EntryType.CREDIT,
        models.LedgerEntry.account_id != SYSTEM_ACCOUNT_ID # Assuming user is the non-system
    ).first()

    if not original_credit_entry:
        raise ValueError("Could not find original credit entry to reverse")
    
    amount = original_credit_entry.amount
    user_id = original_credit_entry.account_id

    # Create Reversal Entries (Debit User, Credit System)
    entry_debit = models.LedgerEntry(
        transaction_id=tx_id,
        account_id=user_id,
        entry_type=models.EntryType.DEBIT,
        amount=amount
    )
    
    entry_credit = models.LedgerEntry(
        transaction_id=tx_id,
        account_id=SYSTEM_ACCOUNT_ID,
        entry_type=models.EntryType.CREDIT,
        amount=amount
    )
    
    db.add(entry_debit)
    db.add(entry_credit)
    
    # Update Balances
    user_account = db.query(models.Account).filter(models.Account.id == user_id).first()
    system_account = db.query(models.Account).filter(models.Account.id == SYSTEM_ACCOUNT_ID).first()
    
    user_account.current_balance -= amount
    system_account.current_balance += amount
    
    # Mark original as reversed (optional, or just track via link)
    original_tx.status = models.TransactionStatus.REVERSED
    
    db.commit()
    return transaction
