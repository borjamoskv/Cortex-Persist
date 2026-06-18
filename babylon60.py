#!/usr/bin/env python3
# C5-REAL
import sys

def parse_b60_digit(token):
    if token == '-': 
        return 0
    tens = token.count('<')
    ones = token.count('Y') + token.count('v') + token.count('T')
    return tens * 10 + ones

def parse_b60_number(b60_str):
    inner = b60_str.strip('[]').strip()
    if not inner: 
        return 0
    places = inner.split()
    total = 0
    power = len(places) - 1
    for p in places:
        val = parse_b60_digit(p)
        total += val * (60 ** power)
        power -= 1
    return total

def format_b60(val):
    if val == 0: return "[-]"
    places = []
    while val > 0:
        places.append(val % 60)
        val //= 60
    places.reverse()
    
    out = []
    for p in places:
        if p == 0:
            out.append("-")
        else:
            tens = p // 10
            ones = p % 10
            out.append("<" * tens + "Y" * ones)
    return "[ " + " ".join(out) + " ]"

class Babylon60:
    def __init__(self):
        self.memory = {}

    def eval_expr(self, expr):
        if expr.startswith('['):
            return parse_b60_number(expr)
        else:
            return self.memory.get(expr, 0)

    def run(self, code):
        for line in code.split('\n'):
            line = line.split('#')[0].strip()
            if not line: continue
            
            tokens = []
            in_bracket = False
            cur = ""
            for char in line:
                if char == '[':
                    in_bracket = True
                    cur += char
                elif char == ']':
                    in_bracket = False
                    cur += char
                    tokens.append(cur.strip())
                    cur = ""
                elif char.isspace() and not in_bracket:
                    if cur:
                        tokens.append(cur)
                        cur = ""
                else:
                    cur += char
            if cur:
                tokens.append(cur)
                
            cmd = tokens[0]
            if cmd == 'DUB':       # Tablet initialization
                pass
            elif cmd == 'SAR':     # Print Decimal
                val = self.eval_expr(tokens[1])
                print(f"SAR (DEC): {val}")
            elif cmd == 'SAR.B60': # Print Base-60
                val = self.eval_expr(tokens[1])
                print(f"SAR (B60): {format_b60(val)}")
            elif cmd == 'NIG':     # Assign
                self.memory[tokens[1]] = self.eval_expr(tokens[2])
            elif cmd == 'DAH':     # Add
                self.memory[tokens[1]] = self.memory.get(tokens[1], 0) + self.eval_expr(tokens[2])
            elif cmd == 'LAL':     # Subtract
                self.memory[tokens[1]] = self.memory.get(tokens[1], 0) - self.eval_expr(tokens[2])
            elif cmd == 'ARA':     # Multiply
                self.memory[tokens[1]] = self.memory.get(tokens[1], 0) * self.eval_expr(tokens[2])
            elif cmd == 'BA':      # Divide
                divisor = self.eval_expr(tokens[2])
                if divisor != 0:
                    self.memory[tokens[1]] = self.memory.get(tokens[1], 0) // divisor
            else:
                print(f"Unknown command: {cmd}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 babylon60.py <script.b60>")
        sys.exit(1)
    
    with open(sys.argv[1], 'r') as f:
        code = f.read()
    
    interpreter = Babylon60()
    interpreter.run(code)
