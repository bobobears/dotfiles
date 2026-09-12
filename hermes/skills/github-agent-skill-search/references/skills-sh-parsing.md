# skills.sh Parsing Reference

## Architecture Change (2026-07)

skills.sh migrated from traditional Next.js SSR (`__NEXT_DATA__`) to **Next.js React Server Components (RSC)** streaming format.

### Old format (broken)
- Data in `<script id="__NEXT_DATA__">` JSON blob
- No public API endpoints

### New format (current)
- Data streamed in `self.__next_f.push([1,"..."])` chunks
- No public API (`/api/skills`, `/api/leaderboard` → 404)
- Skills leaderboard is in `initialSkills` key inside one of the chunks

### Parsing recipe

```python
import re, json

# 1. Fetch HTML
html = subprocess.run(["curl", "-sL", "--max-time", "15", "https://www.skills.sh/"],
                      capture_output=True, text=True).stdout

# 2. Extract all RSC chunks
blocks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.DOTALL)

# 3. Find the block with initialSkills (usually block index 12)
skills_block = next(b for b in blocks if 'initialSkills' in b)

# 4. Locate escaped key and extract array
idx = skills_block.find('\\"initialSkills\\"')
section = skills_block[idx:]
bracket = section.find('[')
array_part = section[bracket:].replace('\\"', '"')

# 5. Match brackets to find array boundary
depth = 0
for i, ch in enumerate(array_part):
    if ch == '[': depth += 1
    elif ch == ']':
        depth -= 1
        if depth == 0:
            array_str = array_part[:i+1]
            break

# 6. Parse and sort
skills = json.loads(array_str)
skills.sort(key=lambda s: s.get("installs", 0), reverse=True)
```

### Data shape

Each skill object:
```json
{
  "source": "owner/repo",
  "skillId": "skill-name",
  "name": "Skill Name",
  "installs": 12345,
  "weeklyInstalls": [100, 200, 300, ...]
}
```

### Pitfalls

- The regex `self\.__next_f\.push\(\[1,"(.*?)"\]\)` uses non-greedy `.*?` — critical because chunks contain nested brackets
- `initialSkills` key is **escaped** as `\"initialSkills\"` inside the chunk string (double backslash in Python: `\\"initialSkills\\"`)
- After unescaping, the array can contain nested arrays (weeklyInstalls), so bracket matching is required — simple `split(']')` will fail
- Total skills: ~600+, total installs: ~900k+ (as of 2026-07)
- The `top-hermes-skills.py` script in `~/.hermes/scripts/` uses this parsing logic — update it if skills.sh changes format again
