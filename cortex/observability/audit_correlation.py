# [C5-REAL] Exergy-Maximized
import glob
import json
import os
import random


def audit_correlation(num_sessions=20):
    base_dir = os.path.expanduser("~/.gemini/antigravity/brain")
    transcripts = glob.glob(f"{base_dir}/*/.system_generated/logs/transcript.jsonl")

    if not transcripts:
        print("No transcripts found.")
        return

    sampled = random.sample(transcripts, min(num_sessions, len(transcripts)))

    total_calls = 0
    matched_calls = 0
    mismatches = []

    # Map from tool name to expected transcript type
    TAXONOMY_MAP = {
        "list_dir": "list_directory",
        "write_to_file": "code_action",
        "replace_file_content": "code_action",
        "multi_replace_file_content": "code_action",
        "run_command": "execute_command",
        "schedule": "generic",
        "send_message": "generic",
        "ask_question": "generic",
        "grep_search": "search",
        "search_web": "search_web",
        "read_url_content": "read_url_content",
    }

    for t in sampled:
        try:
            with open(t, encoding="utf-8") as fh:
                lines = [json.loads(line) for line in fh if line.strip()]
        except (ValueError, TypeError, OSError, KeyError):
            continue

        i = 0
        while i < len(lines):
            step = lines[i]
            if step.get("type") == "PLANNER_RESPONSE" and "tool_calls" in step:
                tool_calls = step["tool_calls"]

                for j, call in enumerate(tool_calls):
                    if i + 1 + j < len(lines):
                        result_step = lines[i + 1 + j]
                        expected_tool = call.get("name", "").lower()
                        actual_type = result_step.get("type", "").lower()

                        expected_type = TAXONOMY_MAP.get(expected_tool, expected_tool)

                        if (
                            actual_type == expected_type
                            or actual_type == expected_tool
                            or expected_tool.startswith("mcp_")
                            or actual_type == "call_mcp_tool"
                        ):
                            matched_calls += 1
                        else:
                            mismatches.append(
                                {
                                    "transcript": t,
                                    "step_index": i + 1 + j,
                                    "expected_tool": expected_tool,
                                    "actual_type": actual_type,
                                    "result_step": result_step,
                                }
                            )
                    total_calls += 1
                i += 1 + len(tool_calls)
            else:
                i += 1

    accuracy = (matched_calls / total_calls * 100) if total_calls > 0 else 0
    print("--- CORRELATION AUDIT ---")
    print(f"Sessions sampled: {len(sampled)}")
    print(f"Total tool calls checked: {total_calls}")
    print(f"Matches found: {matched_calls}")
    print(f"Precision: {accuracy:.2f}%")

    if mismatches:
        print(f"\nFound {len(mismatches)} mismatches. Examples:")
        for m in mismatches[:10]:
            print(
                f" - Expected: {m['expected_tool']}, Actual step type: {m['actual_type']} in {os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(m['transcript']))))}"
            )


if __name__ == "__main__":
    audit_correlation(20)
