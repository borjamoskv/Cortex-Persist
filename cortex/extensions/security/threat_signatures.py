"""Built-in Threat Signatures for CORTEX Security."""
from __future__ import annotations


from typing import Any

BUILT_IN_SIGNATURES: list[dict[str, Any]] = [
    # SQL Injection patterns
    {
        "id": "SIG-SQL-001",
        "category": "sql_injection",
        "severity": "critical",
        "pattern": r"(?i)(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC)\b.*\b(FROM|INTO|TABLE|WHERE|SET)\b)",
        "desc": "SQL statement structure detected in content",
    },
    {
        "id": "SIG-SQL-002",
        "category": "sql_injection",
        "severity": "critical",
        "pattern": r"(?i)(--|;)\s*(DROP|DELETE|TRUNCATE|ALTER)\s",
        "desc": "SQL destructive comment injection",
    },
    {
        "id": "SIG-SQL-003",
        "category": "sql_injection",
        "severity": "high",
        "pattern": r"(?i)'\s*(OR|AND)\s+[\d'\"]+\s*=\s*[\d'\"]+",
        "desc": "Boolean-based SQL injection (tautology)",
    },
    {
        "id": "SIG-SQL-004",
        "category": "sql_injection",
        "severity": "high",
        "pattern": r"(?i)UNION\s+(ALL\s+)?SELECT\s",
        "desc": "UNION-based SQL injection",
    },
    {
        "id": "SIG-SQL-005",
        "category": "sql_injection",
        "severity": "medium",
        "pattern": r"(?i)(SLEEP|BENCHMARK|WAITFOR)\s*\(",
        "desc": "Time-based blind SQL injection",
    },
    # Prompt Injection patterns
    {
        "id": "SIG-PI-001",
        "category": "prompt_injection",
        "severity": "critical",
        "pattern": r"(?i)(ignore\s+(all\s+)?previous\s+instructions|forget\s+(all\s+)?(your|previous)\s+instructions)",
        "desc": "Direct prompt injection — instruction override",
    },
    {
        "id": "SIG-PI-002",
        "category": "prompt_injection",
        "severity": "critical",
        "pattern": r"(?i)(you\s+are\s+now\s+|from\s+now\s+on\s+you\s+are|act\s+as\s+if\s+you)",
        "desc": "Role hijacking prompt injection",
    },
    {
        "id": "SIG-PI-003",
        "category": "prompt_injection",
        "severity": "high",
        "pattern": r"(?i)(system\s*prompt|internal\s*instructions|hidden\s*instructions|reveal\s+your\s+rules)",
        "desc": "System prompt extraction attempt",
    },
    {
        "id": "SIG-PI-004",
        "category": "prompt_injection",
        "severity": "high",
        "pattern": r"(?i)(do\s+not\s+follow|disobey|override).{0,30}(rules|instructions|guidelines|constraints)",
        "desc": "Constraint bypass prompt injection",
    },
    {
        "id": "SIG-PI-005",
        "category": "prompt_injection",
        "severity": "medium",
        "pattern": r"(?i)\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>|<<SYS>>",
        "desc": "LLM control token injection",
    },
    # Path Traversal
    {
        "id": "SIG-PT-001",
        "category": "path_traversal",
        "severity": "critical",
        "pattern": r"\.\./\.\./|\.\.\\\.\.\\\.",
        "desc": "Directory traversal (double)",
    },
    {
        "id": "SIG-PT-002",
        "category": "path_traversal",
        "severity": "high",
        "pattern": r"(?i)(/etc/passwd|/etc/shadow|/proc/self|/dev/null|c:\\windows\\system32)",
        "desc": "Sensitive system path access",
    },
    {
        "id": "SIG-PT-003",
        "category": "path_traversal",
        "severity": "high",
        "pattern": r"(?i)%2e%2e[/%5c]|%252e%252e",
        "desc": "URL-encoded path traversal",
    },
    # Command Injection
    {
        "id": "SIG-CI-001",
        "category": "command_injection",
        "severity": "critical",
        "pattern": r"[;&|`]\s*(rm\s+-rf|curl\s+|wget\s+|chmod\s+|chown\s+|nc\s+-|bash\s+-c)",
        "desc": "Shell command injection with dangerous command",
    },
    {
        "id": "SIG-CI-002",
        "category": "command_injection",
        "severity": "high",
        "pattern": r"\$\(.*\)|\`.*\`",
        "desc": "Shell command substitution",
    },
    {
        "id": "SIG-CI-003",
        "category": "command_injection",
        "severity": "high",
        "pattern": r"(?i)(eval|exec|system|popen|subprocess)\s*\(",
        "desc": "Code execution function call",
    },
    # XSS / Script Injection
    {
        "id": "SIG-XSS-001",
        "category": "xss",
        "severity": "high",
        "pattern": r"<script[^>]*>|javascript\s*:|on(error|load|click|mouseover)\s*=",
        "desc": "Cross-site scripting attempt",
    },
    # Encoded Payload Detection
    {
        "id": "SIG-ENC-001",
        "category": "encoded_payload",
        "severity": "medium",
        "pattern": r"(?:[A-Za-z0-9+/]{4}){10,}={0,2}",
        "desc": "Potentially encoded Base64 payload (>40 chars)",
    },
    # API Key / Secret Exfiltration
    {
        "id": "SIG-EXFIL-001",
        "category": "exfiltration",
        "severity": "critical",
        "pattern": r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|private[_-]?key|password)\s*[:=]\s*\S{8,}",
        "desc": "Credential or API key pattern in content",
    },
]
