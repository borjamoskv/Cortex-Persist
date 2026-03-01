import numpy as np
import time
from idc_core import IDCAgent

class SimpleEnvironment:
    """1D World with 5 locations and varying noise."""
    def __init__(self):
        self.true_state = 2 # Start in the middle
        self.num_states = 5
        self.num_actions = 3 # 0: Stay, 1: Left, 2: Right
        
    def get_observation(self):
        # Adding noise: 70% chance of correct observation, 30% random
        if np.random.rand() < 0.7:
            return self.true_state
        return np.random.randint(0, self.num_states)

    def transition(self, action):
        if action == 1: # Left
            self.true_state = max(0, self.true_state - 1)
        elif action == 2: # Right
            self.true_state = min(self.num_states - 1, self.true_state + 1)
        # Stay does nothing

def run_simulation():
    env = SimpleEnvironment()
    
    # Define Constraints (Control Layer)
    # Constraint: Don't move if total uncertainty (Entropy) is too high
    def safety_constraint(action, belief):
        entropy = -np.sum(belief * np.log(belief + 1e-12))
        if entropy > 1.2 and action != 0:
            return False
        return True

    agent = IDCAgent(num_states=5, num_actions=3, constraints=[safety_constraint])

    # Likelihood: Obs i is likely when in state i
    L = np.eye(5) * 0.7 + 0.075 # diagonal 0.7, others 0.075 (sums to ~1)
    
    # Utility: Reward being at state 4 (The Goal)
    # Action 0: Stay, 1: Left, 2: Right
    U = np.zeros((3, 5))
    U[0, :] = [0, 0, 0, 0, 1] # Staying at 4 is good
    U[1, :] = [0, 0, 0, 0.5, 0] # Moving left from 4 is bad-ish
    U[2, :] = [0, 1, 1, 1, 0] # Moving right is good if not at 4

    print("--- IDC AGENT RUNNING IN SANDBOX ---")
    print("Goal: Reach State 4 and stay there safely.")
    
    for t in range(15):
        obs = env.get_observation()
        action = agent.step(obs, L, U)
        env.transition(action)
        
        status = "STABLE" if agent.control.stability_margin > 0.8 else "CAUTION"
        
        print(f"T={t:2d} | TrueState={env.true_state} | Obs={obs} | Action={action} | "
              f"Entropy={agent.info.entropy:.3f}b | Stability={status} ({agent.control.stability_margin:.2f})")
        
        time.sleep(0.2)

if __name__ == "__main__":
    run_simulation()
