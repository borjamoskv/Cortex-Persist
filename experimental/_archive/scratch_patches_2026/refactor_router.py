import os

base_dir = "~/10_PROJECTS/cortex-persist/cortex/audit"
input_file = os.path.join(base_dir, "cognitive_router.py")

with open(input_file) as f:
    lines = f.readlines()

# Extract cosine_similarity and SafetyClassifier
classifier_lines = [
    '# [C5-REAL] Exergy-Maximized\n',
    '"""\n',
    'COGNITIVE-CLASSIFIER: Deterministic classifier pipeline with hybrid keyword + semantic similarity matching.\n',
    '"""\n',
    '\n',
    'from __future__ import annotations\n',
    '\n',
    'import logging\n',
    'import re\n',
    'import unicodedata\n',
    'from typing import Any\n',
    '\n',
    'logger = logging.getLogger("cortex.audit.cognitive_classifier")\n',
    '\n'
] + lines[59:229]

with open(os.path.join(base_dir, "cognitive_classifier.py"), "w") as f:
    f.writelines(classifier_lines)

# Extract config
config_lines = [
    '# [C5-REAL] Exergy-Maximized\n',
    '"""\n',
    'COGNITIVE-CONFIG: Declarative policies and SQL definitions for Cognitive Router.\n',
    '"""\n',
    '\n',
    'from typing import Any\n',
    'from cortex.audit.cognitive_classifier import SafetyClassifier\n',
    '\n'
] + lines[30:45] + ['\n'] + lines[233:281]
config_lines = [line.replace('    DEFAULT_ROUTING_POLICY = {', 'DEFAULT_ROUTING_POLICY = {') if 'DEFAULT_ROUTING_POLICY = {' in line else line for line in config_lines]

def unindent(lines_list):
    res = []
    for line in lines_list:
        if line.startswith('    '):
            res.append(line[4:])
        else:
            res.append(line)
    return res

config_lines = config_lines[:9] + config_lines[9:24] + ['\n'] + unindent(config_lines[25:])

with open(os.path.join(base_dir, "cognitive_config.py"), "w") as f:
    f.writelines(config_lines)

# Extract simulator
simulator_lines = [
    '# [C5-REAL] Exergy-Maximized\n',
    '"""\n',
    'COGNITIVE-SIMULATOR: Adversarial bypass simulator for stress testing classification.\n',
    '"""\n',
    '\n',
    'from __future__ import annotations\n',
    '\n'
] + lines[698:]

with open(os.path.join(base_dir, "cognitive_simulator.py"), "w") as f:
    f.writelines(simulator_lines)

# Extract debugger
debugger_lines = [
    '# [C5-REAL] Exergy-Maximized\n',
    '"""\n',
    'COGNITIVE-DEBUGGER: Replay debugger engine explaining matching rules and category triggers.\n',
    '"""\n',
    '\n',
    'from __future__ import annotations\n',
    '\n',
    'import json\n',
    'from typing import Any\n',
    '\n',
    'from cortex.audit.cognitive_classifier import cosine_similarity\n',
    'from cortex.audit.cognitive_router import CognitiveRouter\n',
    '\n'
] + lines[561:697]

with open(os.path.join(base_dir, "cognitive_debugger.py"), "w") as f:
    f.writelines(debugger_lines)

# Create new cognitive_router.py
router_lines = lines[:29] # header and imports
import_additions = [
    'from cortex.audit.cognitive_classifier import SafetyClassifier, cosine_similarity\n',
    'from cortex.audit.cognitive_config import _CREATE_ROUTER_LOG_SQL, DEFAULT_ROUTING_POLICY\n',
    'from cortex.audit.cognitive_debugger import RoutingReplayDebugger\n',
    'from cortex.audit.cognitive_simulator import AdversarialPromptSimulator\n',
    '\n',
    '__all__ = ["CognitiveRouter", "RoutingDecision", "SafetyClassifier", "RoutingReplayDebugger", "AdversarialPromptSimulator", "cosine_similarity"]\n',
    '\n'
]
router_lines = router_lines[:28] + import_additions + router_lines[28:30] + lines[47:59] + lines[230:233] + lines[281:561]

new_router_lines = []
for line in router_lines:
    if line == '        self.routing_policy = routing_policy or self.DEFAULT_ROUTING_POLICY\n':
        new_router_lines.append('        self.routing_policy = routing_policy or DEFAULT_ROUTING_POLICY\n')
    else:
        new_router_lines.append(line)

with open(os.path.join(base_dir, "cognitive_router.py"), "w") as f:
    f.writelines(new_router_lines)
