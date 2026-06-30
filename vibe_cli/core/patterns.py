def detect_pattern(state):
    files_lower = [f.lower() for f in state.files]
    modules = state.current_architecture.get("modules_detected", [])
    modules_lower = [m.lower() for m in modules]

    scores = {
        "MVC": 0,
        "Clean Architecture": 0,
        "Monolito Modular": 0,
        "Script-based": 0,
        "Microservices": 0
    }

    # MVC signals
    mvc_keywords = ["controller", "view", "model", "template"]
    for kw in mvc_keywords:
        if any(kw in f for f in files_lower):
            scores["MVC"] += 2
        if any(kw in m for m in modules_lower):
            scores["MVC"] += 2

    # Clean Architecture signals
    clean_keywords = ["usecase", "repository", "entity", "domain", "infrastructure"]
    for kw in clean_keywords:
        if any(kw in f for f in files_lower):
            scores["Clean Architecture"] += 2
        if any(kw in m for m in modules_lower):
            scores["Clean Architecture"] += 2

    # Monolito modular
    if len(modules) >= 4:
        scores["Monolito Modular"] += 3

    # Script-based
    total_functions = state.current_architecture.get("total_functions", 0)
    total_classes = state.current_architecture.get("total_classes", 0)
    if total_functions > total_classes * 2:
        scores["Script-based"] += 3

    # Microservices
    micro_keywords = ["service", "gateway", "proxy", "worker"]
    for kw in micro_keywords:
        if any(kw in m for m in modules_lower):
            scores["Microservices"] += 2

    detected = max(scores, key=scores.get)
    confidence = scores[detected]

    return {
        "pattern": detected,
        "confidence_score": confidence,
        "all_scores": scores
    }
