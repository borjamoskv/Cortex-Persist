import ast,json,os
from pathlib import Path

def get_ast(path):
    try:
        t=ast.parse(open(path).read())
        return sum(1 for n in ast.walk(t) if isinstance(n,ast.Global))
    except:
        return 0

def main():
    d=[]
    for r,_,f in os.walk("cortex-core"):
        for n in f:
            if n.endswith(".py") and len(d)<76:
                p=os.path.join(r,n)
                d.append({"file":p,"pattern":get_ast(p)>0})
    with open(".cortex_ast_dataset.json","w") as f:
        json.dump(d,f)
if __name__=="__main__":
    main()
