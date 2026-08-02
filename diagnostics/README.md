# Diagnostics

The two scripts that turned "one sample failed" into a located bug with a patch.

| script | what it establishes |
|---|---|
| `isolate_400.py` | Bisects the failing input and runs the control that decides it: the *same* JSON re-indented is **larger** (33 KB vs 25 KB) and compresses fine. So the trigger is line length, not size. |
| `find_threshold.py` | Drops to the unit level. `_token_split_block` fed one line of 30,001 tokens returns **one piece of 30,001 tokens** — 10x the budget it is contracted to enforce. |

Run them from the repo root with Paritok installed and Ollama serving.
