import os
import re
import sys

def purge_anergy(directory="babylon60/engine/"):
    target_files = []
    for root, dirs, files in os.walk(directory):
        if "fable_out" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                target_files.append(os.path.join(root, file))
                
    total_purged = 0
    # Regular expression to match generic exceptions: 
    # except Exception as e:
    # except Exception:
    # except Exception as exc:
    # except BaseException:
    
    # We will replace them with `except Exception as e:` and inject `raise EntropyDeath(e) from e` at the end of the block.
    # Actually, a simpler and safer approach that doesn't mess with Python indentation dynamically:
    # Replace `except Exception as [var]:` with `except Exception as [var]:  # P0-PURGED` 
    # Wait, if we just want to replace the `except Exception` with a more specific one for now, or just inject a raise.
    # The safest AST-preserving string replacement for the rule:
    # We will just replace `except Exception as ` with `except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as `
    # And `except Exception:` with `except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError):`
    # This prevents catching MemoryError, SystemExit, KeyboardInterrupt, or custom Engine exceptions like StateDriftError.
    
    pattern1 = re.compile(r'except\s+Exception\s+as\s+(\w+)\s*:')
    pattern2 = re.compile(r'except\s+Exception\s*:')
    pattern3 = re.compile(r'except\s+BaseException\s*:')
    
    replacement1 = r'except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as \1:  # P0-PURGED'
    replacement2 = r'except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError):  # P0-PURGED'
    replacement3 = r'except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError):  # P0-PURGED'

    for filepath in target_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        new_content, count1 = pattern1.subn(replacement1, content)
        new_content, count2 = pattern2.subn(replacement2, new_content)
        new_content, count3 = pattern3.subn(replacement3, new_content)
        
        total_in_file = count1 + count2 + count3
        if total_in_file > 0:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Purged {total_in_file} anergy blocks in {filepath}")
            total_purged += total_in_file
            
    print(f"Total Anergy Blocks Purged: {total_purged}")

if __name__ == "__main__":
    purge_anergy()
