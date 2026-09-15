TOTAL_BUDGET = 2.00
spent = 0.0
request_log = []

def check_budget(estimated_cost: float):
    global spent
    remaining = max(0.0, round(TOTAL_BUDGET - spent, 4))
    if spent + estimated_cost > TOTAL_BUDGET:
        return {
            "allowed": False,
            "reason": "Budget exceeded",
            "spent": round(spent, 4),
            "remaining": remaining
        }
    return {
        "allowed": True,
        "spent": round(spent, 4),
        "remaining": remaining
    }

def record_spend(cost: float, prompt: str, model: str):
    global spent
    if cost > 0:
        spent += cost
    request_log.append({
        "prompt_preview": prompt[:50],
        "model": model,
        "cost": cost,
        "total_spent": round(spent, 4)
    })

def get_stats():
    remaining = max(0.0, round(TOTAL_BUDGET - spent, 4))
    return {
        "total_budget": TOTAL_BUDGET,
        "spent": round(spent, 4),
        "remaining": remaining,
        "percent_used": round((spent / TOTAL_BUDGET) * 100, 1),
        "requests": len(request_log),
        "log": request_log
    }