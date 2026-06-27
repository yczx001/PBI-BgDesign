"""Extract a task from the plan file."""
import sys
import re

plan_path = sys.argv[1]
task_num = int(sys.argv[2])

with open(plan_path, "r", encoding="utf-8") as f:
    content = f.read()

# Split by task headers
tasks = re.split(r'(?=### Task \d+:)', content)
for t in tasks:
    match = re.match(r'### Task (\d+):', t)
    if match and int(match.group(1)) == task_num:
        # Find end (next task or end)
        print(t.strip())
        break
