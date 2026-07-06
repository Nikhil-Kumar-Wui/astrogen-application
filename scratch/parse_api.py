import re

with open("frontend/lib/api-client-react/src/generated/api.ts", "r", encoding="utf-8") as f:
    data = f.read()

paths = set(re.findall(r'"/[^"]*"|\'/[^\']*\'|`/[^`]*`', data))
for p in sorted(paths):
    print(p)
