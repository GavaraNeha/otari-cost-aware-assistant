def analyze_complexity(prompt: str):
    words = prompt.split()
    word_count = len(words)
    
    complex_keywords = [
        "explain", "analyze", "compare", "calculate", "code",
        "write", "build", "design", "create", "implement",
        "difference", "how does", "why does", "summarize"
    ]
    
    keyword_hits = sum(1 for kw in complex_keywords 
                      if kw in prompt.lower())
    
    score = min(100, (word_count * 2) + (keyword_hits * 15))
    
    if score < 30:
        return {"level": "simple", "score": score, 
                "model": "smallest-ai-fast", "cost": 0.001}
    elif score < 65:
        return {"level": "medium", "score": score, 
                "model": "smallest-ai-balanced", "cost": 0.003}
    else:
        return {"level": "complex", "score": score, 
                "model": "smallest-ai-pro", "cost": 0.008}