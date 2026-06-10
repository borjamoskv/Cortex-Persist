import os
import random

def inject_determinism(seed: int = 42):
    """
    Enforce C5-REAL determinism by setting standard random seeds and 
    environment variables that control hashing and randomness across
    the Python runtime and cryptographic libraries.
    """
    # Python stdlib random
    random.seed(seed)
    
    # Environment variables
    os.environ["PYTHONHASHSEED"] = str(seed)
    
    # Try to set numpy seed if it's available
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    
    # Try to set torch seed if it's available
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass
