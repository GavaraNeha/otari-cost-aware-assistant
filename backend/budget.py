TOTAL_BUDGET = 2.00
spent = 0.0
request_log = []

def check_budget(estimated_cost: float):
    global spent
    if spent + estimated_cost > TOTAL_BUDGET:
        return {
            "allowed": False,
            "reason": "Budget exceeded",
            "spent": spent,
            "remaining": round(TOTAL_BUDGET - spent, 4)
        }
    return {
        "allowed": True,
        "spent": spent,
        "remaining": round(TOTAL_BUDGET - spent, 4)
    }

def record_spend(cost: float, prompt: str, model: str):
    global spent
    spent += cost
    request_log.append({
        "prompt_preview": prompt[:50],
        "model": model,
        "cost": cost,
        "total_spent": round(spent, 4)
    })

def get_stats():
    return {
        "total_budget": TOTAL_BUDGET,
        "spent": round(spent, 4),
        "remaining": round(TOTAL_BUDGET - spent, 4),
        "percent_used": round((spent / TOTAL_BUDGET) * 100, 1),
        "requests": len(request_log),
        "log": request_log
    }