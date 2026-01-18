from typing import List, Dict, Any
from . import schemas

def evaluate_condition(condition: schemas.RuleCondition, context: Dict[str, Any]) -> bool:
    # simple dot notation support e.g. "referrer.status"
    keys = condition.field.split('.')
    value = context
    try:
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return False
    except:
        return False

    if condition.operator == 'eq':
        return str(value).lower() == str(condition.value).lower()
    elif condition.operator == 'gt':
        return float(value) > float(condition.value)
    elif condition.operator == 'lt':
        return float(value) < float(condition.value)
    elif condition.operator == 'contains':
        return condition.value in str(value)
    
    return False

def evaluate_rule(rule: schemas.Rule, context: Dict[str, Any]) -> List[schemas.RuleAction]:
    results = [evaluate_condition(cond, context) for cond in rule.conditions]
    
    is_triggered = False
    if rule.operator == 'AND':
        is_triggered = all(results)
    elif rule.operator == 'OR':
        is_triggered = any(results)
        
    if is_triggered:
        return rule.actions
    return []

def run_flow(rules: List[schemas.Rule], context: Dict[str, Any]):
    actions_to_take = []
    for rule in rules:
        actions = evaluate_rule(rule, context)
        actions_to_take.extend(actions)
    return actions_to_take
