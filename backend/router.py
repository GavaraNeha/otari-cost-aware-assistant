from complexity import analyze_complexity

def route_prompt(prompt: str):
    complexity = analyze_complexity(prompt)
    
    routing_table = {
        "simple": {
            "model": "smallest-ai-fast",
            "reason": "Simple query — fast cheap model selected",
            "expected_latency": "< 1s"
        },
        "medium": {
            "model": "smallest-ai-balanced", 
            "reason": "Medium complexity — balanced model selected",
            "expected_latency": "1-2s"
        },
        "complex": {
            "model": "smallest-ai-pro",
            "reason": "Complex reasoning required — pro model selected",
            "expected_latency": "2-4s"
        }
    }
    
    route = routing_table[complexity["level"]]
    
    return {
        "model": route["model"],
        "reason": route["reason"],
        "latency": route["expected_latency"],
        "complexity_score": complexity["score"],
        "complexity_level": complexity["level"],
        "cost": complexity["cost"]
    }