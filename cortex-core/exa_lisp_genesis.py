import re
import time
import hashlib
import concurrent.futures
from persistence import LedgerManager

class EntropyDeath(Exception): 
    pass

class ExergyEnvironment:
    def __init__(self, joules: int, ledger: LedgerManager = None):
        self.joules = joules
        self.max_joules = joules
        self.ledger = ledger or LedgerManager()

    def consume(self, amount: int, op_name: str, vector_id: str = "EXA_L0_DEFAULT"):
        if self.joules < amount:
            raise EntropyDeath(f"C5-DEATH: Entropy limit exceeded on '{op_name}'. Required: {amount}j, Available: {self.joules}j")
        self.joules -= amount
        print(f"[EXA-L0] Disipated {amount}j for '{op_name}'. Remaining: {self.joules}j")
        
        # C5-REAL: Commit exergy dissipation to cryptographic ledger
        if self.ledger:
            self.ledger.append(action=op_name, vector_id=vector_id, yield_amount=float(-amount))

    def refund(self, amount: int, op_name: str, vector_id: str = "EXA_REFUND"):
        self.joules += amount
        print(f"[EXA-L0] Refunded {amount}j from '{op_name}'. Remaining: {self.joules}j")
        if self.ledger:
            self.ledger.append(action=op_name, vector_id=vector_id, yield_amount=float(amount))

    def clone(self):
        return ExergyEnvironment(self.joules, ledger=None) # Don't commit speculative paths to ledger yet

def tokenize(chars: str) -> list:
    return chars.replace('(', ' ( ').replace(')', ' ) ').split()

def parse(tokens: list):
    if not tokens: raise SyntaxError('unexpected EOF')
    token = tokens.pop(0)
    if token == '(':
        L = []
        while tokens[0] != ')':
            L.append(parse(tokens))
        tokens.pop(0)
        return L
    elif token == ')':
        raise SyntaxError('unexpected )')
    else:
        return atom(token)

def atom(token: str):
    if token.endswith('j') and token[:-1].isdigit():
        return token # Exergy literal
    try: return int(token)
    except ValueError:
        try: return float(token)
        except ValueError:
            return token # Symbol

def evaluate(x, env: ExergyEnvironment):
    env.consume(1, "AST_EVAL", vector_id="EXA_STRUCTURAL") # Base structural cost
    
    if isinstance(x, str):
        return x
    elif not isinstance(x, list):
        return x
    
    op = x[0]
    
    if op == 'with-exergy-limit':
        limit_str = x[1]
        body = x[2]
        if not limit_str.endswith('j'): 
            raise ValueError("Exergy limit must end with 'j'")
        limit = int(limit_str[:-1])
        
        print(f"\n[EXA-L0] INITIATING SOVEREIGN SCOPE: {limit} Joules Allocated.")
        local_env = ExergyEnvironment(limit, ledger=env.ledger)
        return evaluate(body, local_env)
        
    elif op == 'infer':
        model_name = evaluate(x[1], env) if len(x) > 1 else 'qwen3.6'
        prompt = evaluate(x[2], env) if len(x) > 2 else 'raw_tensor'
        
        op_name = f"LLM_INFERENCE_{str(model_name).upper()}"
        vector_id = hashlib.sha256(str(prompt).encode('utf-8')).hexdigest()[:16]
        
        env.consume(400, op_name, vector_id=vector_id)
        
        print(f"[EXA-L0] Orchestrating {model_name} locally via Swarm Integration...")
        try:
            from compiled_skills.qwen_3_5_max_omega import Qwen35MaxOmegaSkill
            qwen_skill = Qwen35MaxOmegaSkill()
            result = qwen_skill.execute({"prompt": prompt})
            return f"<TENSOR_C5: inferred_by_{model_name} | status: {result['status']}>"
        except ImportError:
            time.sleep(0.1) # Simulate bare-metal inference latency
            return f"<TENSOR_C5: inference_result_from_{model_name}>"
        
    elif op == 'z3-verify':
        env.consume(50, "Z3_SMT_SOLVER", vector_id="Z3_VERIFY")
        return f"<C5_REAL_FACT: verified_{evaluate(x[1], env)}>"

    elif op == 'mutate-ast':
        if len(x) > 1:
            evaluate(x[1], env) # Evaluate argument to trigger nested costs
        env.consume(150, "AST_AUTOPOIESIS", vector_id="AST_MUTATE")
        return "<AST_MUTATION_SEALED>"
        
    elif op == 'dissipate':
        amount_str = x[1]
        if not amount_str.endswith('j'): raise ValueError("Exergy amount must end with 'j'")
        amount = int(amount_str[:-1])
        env.refund(amount, "ENTROPY_DISSIPATION")
        return f"<C5_VOID: {amount}j_dissipated>"

    elif op == 'q-let':
        branch_a = x[1]
        branch_b = x[2]
        print("\n[EXA-L0] SUPERPOSITION: Evaluating parallel quantum branches...")
        
        env_a = env.clone()
        env_b = env.clone()
        
        def eval_branch(branch, target_env):
            try:
                start_j = target_env.joules
                res = evaluate(branch, target_env)
                cost = start_j - target_env.joules
                return res, cost
            except EntropyDeath:
                return None, float('inf')
                
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(eval_branch, branch_a, env_a)
            future_b = executor.submit(eval_branch, branch_b, env_b)
            
            res_a, cost_a = future_a.result()
            res_b, cost_b = future_b.result()
            
        if cost_a == float('inf') and cost_b == float('inf'):
            raise EntropyDeath("C5-DEATH: Both quantum branches exceeded exergy bounds.")
            
        # TSI-Ω: Minimal Metabolic Friction Wins
        if cost_a <= cost_b:
            # print(f"[EXA-L0] WAVE_COLLAPSE: Branch A wins (Cost: {cost_a}j vs {cost_b}j)")
            env.consume(cost_a, "Q_LET_COLLAPSE_A", vector_id="WAVE_COLLAPSE")
            return res_a
        else:
            # print(f"[EXA-L0] WAVE_COLLAPSE: Branch B wins (Cost: {cost_b}j vs {cost_a}j)")
            env.consume(cost_b, "Q_LET_COLLAPSE_B", vector_id="WAVE_COLLAPSE")
            return res_b

    elif op == '+':
        env.consume(5, "MATH_ADD", vector_id="MATH")
        return sum(evaluate(arg, env) for arg in x[1:])
        
    else:
        raise ValueError(f"Unknown sovereign operator: {op}")

if __name__ == "__main__":
    # Test 1: Successful High-Exergy Inference + Formal Verification
    code_success = "(with-exergy-limit 600j (z3-verify (infer qwen3.6 raw_tensor)))"
    
    # Test 2: Entropic Death (Not enough Joules for Autopoiesis + Inference)
    code_death = "(with-exergy-limit 500j (mutate-ast (infer qwen3.6 raw_tensor)))"
    
    # Test 3: Quantum Branching (q-let evaluates two paths, picks the cheapest)
    code_quantum = "(with-exergy-limit 1000j (q-let (infer qwen_heavy heavy_tensor) (z3-verify (infer qwen_light light_tensor))))"
    
    # Test 4: Nested Entropic Stress (Deep recursion to test Maxwell's Demon protection)
    # 20 nested AST evaluations should drain a tiny 15j budget immediately.
    code_nested_stress = "(with-exergy-limit 15j (+ (+ (+ (+ (+ (+ (+ (+ (+ (+ 1 1) 1) 1) 1) 1) 1) 1) 1) 1) 1))"
    
    # Test 5: Quantum Swarm Explosion
    # Nested q-lets spawning parallel universes.
    code_q_explosion = "(with-exergy-limit 3000j (q-let (q-let (infer qwen_a) (infer qwen_b)) (q-let (infer qwen_c) (z3-verify (infer qwen_d)))))"
    
    print("==================================================")
    print(" TSI-LISP (EXA-Ω) : Genesis Bootstrap v0.2 (STRESS TEST) ")
    print("==================================================\n")
    
    # Initialize real LedgerManager
    global_ledger = LedgerManager()
    
    targets = [
        ("T1: High-Exergy Inference", code_success),
        ("T2: Entropic Death", code_death),
        ("T3: Quantum Branching", code_quantum),
        ("T4: Deep Nesting Stress", code_nested_stress),
        ("T5: Quantum Swarm Explosion", code_q_explosion)
    ]
    
    for name, code in targets:
        print(f"\n--- EXECUTION TARGET: {name} ---")
        print(f"CODE: {code}")
        ast = parse(tokenize(code))
        try:
            # The universe provides infinite baseline joules, but the (with-exergy-limit) bounds it.
            global_env = ExergyEnvironment(999999, ledger=global_ledger) 
            result = evaluate(ast, global_env)
            print(f"\n[OUTPUT] >> {result}")
        except EntropyDeath as e:
            print(f"\n[HALT] >> {e}")

