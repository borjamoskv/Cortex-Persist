import os
import subprocess
import sys
import time


def run_parallel():
    total_frames = 38676
    num_chunks = 4
    chunk_size = total_frames // num_chunks
    
    processes = []
    chunk_files = []
    
    os.makedirs("out", exist_ok=True)
    
    print(f"Starting parallel render of {total_frames} frames split into {num_chunks} chunks...")
    
    for i in range(num_chunks):
        start = i * chunk_size
        # For the last chunk, render to the very end
        end = (start + chunk_size - 1) if i < num_chunks - 1 else total_frames - 1
        
        chunk_file = f"out/chunk_{i}.mp4"
        chunk_files.append(chunk_file)
        
        cmd = [
            "npx", "remotion", "render",
            "src/index.ts", "CortexPresentation", chunk_file,
            f"--frame-range={start}-{end}"
        ]
        
        log_file = open(f"out/chunk_{i}.log", "w")
        print(f"Launching chunk {i}: frames {start} to {end} -> {chunk_file}")
        
        # Start subprocess
        p = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
        processes.append((p, log_file))
        
    # Wait for all processes to complete
    print("All chunks launched. Waiting for render completion...")
    
    completed = [False] * num_chunks
    while not all(completed):
        for idx, (p, _) in enumerate(processes):
            if not completed[idx]:
                status = p.poll()
                if status is not None:
                    if status == 0:
                        print(f"Chunk {idx} finished successfully.")
                        completed[idx] = True
                    else:
                        print(f"Error: Chunk {idx} failed with code {status}. Check logs out/chunk_{idx}.log")
                        # Terminate others
                        for p_other, _ in processes:
                            p_other.kill()
                        sys.exit(1)
        time.sleep(2)
        
    # Close logs
    for _, log_f in processes:
        log_f.close()
        
    # Merge using ffmpeg
    print("All chunks rendered. Merging files...")
    concat_file = "out/files.txt"
    with open(concat_file, "w") as f:
        for chunk in chunk_files:
            f.write(f"file '{os.path.basename(chunk)}'\n")
            
    output_video = "out/video.mp4"
    if os.path.exists(output_video):
        os.remove(output_video)
        
    merge_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file, "-c", "copy", output_video
    ]
    
    print(f"Running merge: {' '.join(merge_cmd)}")
    merge_res = subprocess.run(merge_cmd, capture_output=True, text=True)
    
    if merge_res.returncode == 0:
        print("Merge successful! Video created at out/video.mp4")
        # Cleanup chunks
        for chunk in chunk_files:
            os.remove(chunk)
        os.remove(concat_file)
        # Remove logs
        for i in range(num_chunks):
            os.remove(f"out/chunk_{i}.log")
    else:
        print(f"Merge failed: {merge_res.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    run_parallel()
