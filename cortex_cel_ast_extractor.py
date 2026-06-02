import ast,json,os,subprocess
def get_git(p):
    try:
        a=len(set(subprocess.check_output(["git","log","--format=%an",p],text=True).split()))
        f=subprocess.check_output(["git","log","--oneline",p],text=True).lower().count("fix")
        return max(1,a),f
    except:
        return 1,0
def get_ast(p):
    try:
        c=open(p).read()
        return sum(1 for n in ast.walk(ast.parse(c)) if isinstance(n,ast.Global)),len(c.splitlines())
    except:
        return 0,0
d=[]
for r,_,fs in os.walk("cortex-core"):
    for n in fs:
        if n.endswith(".py") and len(d)<76:
            p=os.path.join(r,n)
            pat,loc=get_ast(p)
            a,f=get_git(p)
            d.append({"file":p,"pattern_present":pat>0,"loc":loc,"authors":a,"failures":f})
with open(".cortex_ast_dataset.json","w") as f:
    json.dump(d,f)
