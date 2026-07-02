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
    # Clean Architecture signals
    clean_keywords = ["usecase", "repository", "entity", "domain", "infrastructure"]
    # Microservices signals
    micro_keywords = ["service", "gateway", "proxy", "worker"]

    # Pre-compute keyword containment in files and modules to minimize nested loops and conditionals
    all_kws = mvc_keywords + clean_keywords + micro_keywords
    matched_files = {kw for kw in all_kws if any(kw in f for f in files_lower)}
    matched_modules = {kw for kw in all_kws if any(kw in m for m in modules_lower)}

    scores["MVC"] = 2 * sum(1 for kw in mvc_keywords if kw in matched_files) + 2 * sum(1 for kw in mvc_keywords if kw in matched_modules)
    scores["Clean Architecture"] = 2 * sum(1 for kw in clean_keywords if kw in matched_files) + 2 * sum(1 for kw in clean_keywords if kw in matched_modules)
    scores["Microservices"] = 2 * sum(1 for kw in micro_keywords if kw in matched_modules)

    # Monolito modular
    if len(modules) >= 4:
        scores["Monolito Modular"] += 3

    # Script-based
    total_functions = state.current_architecture.get("total_functions", 0)
    total_classes = state.current_architecture.get("total_classes", 0)
    if total_functions > total_classes * 2:
        scores["Script-based"] += 3

    detected = max(scores, key=scores.get)
    confidence = scores[detected]

    return {
        "pattern": detected,
        "confidence_score": confidence,
        "all_scores": scores
    }

