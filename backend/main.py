from fastapi import FastAPI, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from . import models, schemas, database, ledger_service, rules_engine
from typing import List, Dict, Any

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="PineOS Referral & Ledger System")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Ledger Endpoints --

@app.post("/transaction/credit", response_model=schemas.TransactionResponse)
def credit_reward(
    tx_data: schemas.TransactionCreate, 
    db: Session = Depends(database.get_db)
):
    """
    Credit a reward to a user.
    """
    # Simply taking the first entry as the user credit for this simple API wrapper
    # In reality, we'd map the generic TransactionCreate to specific logic
    if tx_data.transaction_type != "REWARD_CREDIT":
        raise HTTPException(status_code=400, detail="Invalid transaction type for this endpoint")
        
    user_entry = next((e for e in tx_data.entries if e.entry_type == "CREDIT"), None)
    if not user_entry:
        raise HTTPException(status_code=400, detail="No credit entry found")

    try:
        return ledger_service.process_reward_credit(
            db, 
            user_id=user_entry.account_id, 
            amount=user_entry.amount, 
            reference_id=tx_data.reference_id,
            description=tx_data.metadata_json or "Reward"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transaction/reverse", response_model=schemas.TransactionResponse)
def reverse_reward(
    payload: dict = Body(...),
    db: Session = Depends(database.get_db)
):
    ref_id = payload.get("reference_id")
    reason = payload.get("reason", "Reversal")
    
    try:
        return ledger_service.reverse_reward(db, ref_id, reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/account/{account_id}/balance")
def get_balance(account_id: str, db: Session = Depends(database.get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        return {"account_id": account_id, "balance": 0}
    return {"account_id": account_id, "balance": account.current_balance}

# -- Rule Engine Endpoints --

# In-memory store for demo purposes (would be DB in prod)
SAVED_FLOWS = {}

@app.post("/flows")
def save_flow(flow: dict = Body(...)):
    """Save a UI flow configuration"""
    flow_id = flow.get("id", "default")
    SAVED_FLOWS[flow_id] = flow
    return {"status": "saved", "id": flow_id}

@app.get("/flows/{flow_id}")
def get_flow(flow_id: str):
    if flow_id not in SAVED_FLOWS:
        return {} # Return empty if not found
    return SAVED_FLOWS[flow_id]

@app.post("/rules/evaluate")
def evaluate_rules(
    payload: dict = Body(...)
):
    """
    Evaluate a context against a list of rules.
    Payload: { "context": {...}, "rules": [...] }
    """
    context = payload.get("context", {})
    rules_data = payload.get("rules", [])
    
    # Convert dicts to Rule objects
    rules = []
    for r in rules_data:
        rules.append(schemas.Rule(**r))
        
    actions = rules_engine.run_flow(rules, context)
    return {"actions": actions}

@app.post("/rules/generate")
def generate_rule_from_ai(payload: dict = Body(...)):
    """
    Mock AI generation endpoint. 
    In production, this would call OpenAI/Anthropic API with the user prompt.
    """
    prompt = payload.get("prompt", "").lower()
    
    # Simple keyword detection to simulate AI understanding
    if "referrer" in prompt and "paid" in prompt:
        # User asked for the specific example: "IF referrer is a paid user..."
        return {
            "id": "ai_generated",
            "name": "AI Generated Rule",
            "operator": "AND",
            "conditions": [
                {"field": "referrer.status", "operator": "eq", "value": "paid"},
                {"field": "referred.action", "operator": "eq", "value": "subscribes"}
            ],
            "actions": [
                {"action_type": "credit_reward", "params": {"amount": 500}}
            ]
        }
    
    # Fallback / Generic Rule
    return {
        "id": "ai_generic",
        "name": "Generic Rule",
        "operator": "AND",
        "conditions": [
            {"field": "user.score", "operator": "gt", "value": "100"}
        ],
        "actions": [
            {"action_type": "send_email", "params": {"template": "congrats"}}
        ]
    }

@app.get("/")
def read_root():
    return {"message": "Referral Ledger & Flow Builder System API is running"}
