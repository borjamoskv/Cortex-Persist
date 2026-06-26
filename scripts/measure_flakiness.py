#!/usr/bin/env python3
import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Measure test flakiness by running pytest multiple times")
    parser.add_argument("path", nargs="?", default="tests/", help="Path to tests to run")
    parser.add_argument("-n", "--num-runs", type=int, default=10, help="Number of times to run the tests")
    parser.add_argument("--randomize", action="store_true", help="Use pytest-randomly")
    args = parser.parse_args()

    print(f"Running tests in {args.path} {args.num_runs} times to measure flakiness...")
    
    # Check if pytest-randomly is installed
    cmd = ["pytest", args.path, "-q", "--tb=short"]
    if args.randomize:
        print("Using pytest-randomly to randomize test order.")
    else:
        cmd.append("-p")
        cmd.append("no:randomly")
    
    results = []
    
    for i in range(args.num_runs):
        print(f"\n--- Run {i+1}/{args.num_runs} ---")
        try:
            # We capture output to parse failures if needed, or just rely on exit code
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if result.returncode == 0:
                print("Pass")
                results.append("pass")
            else:
                print(f"FAIL (Exit code {result.returncode})")
                results.append("fail")
                
                # Print a summary of failures from the output
                lines = result.stdout.splitlines()
                fail_lines = [line for line in lines if line.startswith("FAILED ") or line.startswith("ERROR ")]
                for line in fail_lines[:5]:
                    print("  " + line)
                if len(fail_lines) > 5:
                    print(f"  ... and {len(fail_lines) - 5} more failures.")
        except Exception as e:
            print(f"Error running pytest: {e}")
            results.append("error")

    fails = results.count("fail")
    passes = results.count("pass")
    
    print("\n" + "="*40)
    print("Flakiness Report:")
    print(f"Total Runs: {args.num_runs}")
    print(f"Passes: {passes}")
    print(f"Failures: {fails}")
    print(f"Flakiness Rate: {(fails/args.num_runs)*100:.1f}%")
    
    if fails > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
