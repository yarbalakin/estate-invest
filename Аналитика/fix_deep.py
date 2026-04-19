#!/usr/bin/env python3
"""Replace deep_analysis endpoint in main.py with new version from deep_analysis_endpoint.py"""

with open("/opt/torgi-proxy/main.py") as f:
    lines = f.readlines()

# Find deep_analysis start and next @app after it
start = None
end = None
for i, line in enumerate(lines):
    if "@app.get" in line and "deep-analysis" in line:
        start = i
    elif start is not None and i > start + 2 and line.startswith("@app."):
        end = i
        break

if start is None:
    print("NOT FOUND")
    exit(1)

if end is None:
    end = len(lines)

print(f"Removing lines {start}-{end}")

# Read new function
with open("/opt/torgi-proxy/deep_analysis_endpoint.py") as f:
    new_lines = f.readlines()

# Skip docstring/comments, find async def
func_start = 0
for i, line in enumerate(new_lines):
    if line.startswith("async def"):
        func_start = i
        break

func_lines = new_lines[func_start:]

# Fix: add Request type hint
func_lines[0] = func_lines[0].replace("(request,", "(request: Request,")

# Build new block
new_block = ['@app.get("/api/deep-analysis")\n'] + func_lines + ['\n\n']

result = lines[:start] + new_block + lines[end:]

with open("/opt/torgi-proxy/main.py", "w") as f:
    f.writelines(result)
print(f"OK: replaced with {len(new_block)} lines")
