import os
import glob
from grpc_tools import protoc

def compile_protos():
    os.makedirs("pb", exist_ok=True)
    open("pb/__init__.py", "w").close()
    
    proto_dir = "../proto"
    proto_files = glob.glob(os.path.join(proto_dir, "*.proto"))
    
    for pf in proto_files:
        protoc.main((
            '',
            f'-I{proto_dir}',
            '--python_out=./pb',
            '--grpc_python_out=./pb',
            pf,
        ))
    print("C5-REAL: Protobuf definitions compiled successfully.")

if __name__ == "__main__":
    compile_protos()
