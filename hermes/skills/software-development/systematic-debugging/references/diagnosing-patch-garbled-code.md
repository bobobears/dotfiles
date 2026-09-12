# Diagnosing and Fixing Garbled Code from Repeated Bad Patches

## When to Use

When `patch` (or any find-and-replace tool) has been applied multiple times to the same area, and the result is **garbled code**: broken indentation, orphaned lines, partial function bodies, or the patch matched the wrong location.

## Root Cause

`patch`'s fuzzy matching can match a **different occurrence** of the target string than intended, especially when:
- The old_string is short or generic (e.g. `return {"sheet": ..., "details": details}`)
- The same or similar pattern appears elsewhere in the file
- Previous patches have already introduced nearby similar-looking code

Each failed patch compounds the damage by introducing garbage that future patches may match against.

## Diagnostic Flow

### 1. Read the Suspect Area

```bash
read_file(path="backend/main.py", offset=2190, limit=50)
```

Look for:
- Lines with **no indentation** where there should be some (`async def` at column 0 in a nested context)
- **Orphaned fragments** like stray `for d in details:\n    }`
- Line count that has grown suspiciously (the file is now longer than git's version of it)

### 2. Check if the Function Has the Right Signature

Was the original a route handler (`@app.get(...)`) or a plain function? If it lost its decorator or has a renamed `_api_` vs `api_` prefix, it's garbled.

### 3. Determine the Extent of Damage

Read 30-50 lines around the suspect area to find the *exact boundaries* of the garbage. Look for:
- The last **known-good line** before damage
- The first **known-good line** after damage (e.g. the next `@app.get(...)` decorator)

## Fix Strategy: Three Options, Ranked

### Option A: git restore (try first if possible)

```bash
git checkout HEAD -- <file>
```

**Fastest but destroys all in-flight changes.** Only use when the garbled code is the *only* change since the last good commit, or when you can re-apply all other changes fresh.

### Option B: Direct string replacement (best for heavily-patched files)

When git cannot help (e.g. the file grew far beyond the last commit due to many patches):

1. **Read the exact garbage block** — use `read_file` with offsets to capture the exact text, including all whitespace and indentation quirks
2. **Use `repr()` to see hidden characters** — run the block through `repr()` in a Python script, or print it alongside what you expect:
   ```python
   with open("file.py") as f:
       content = f.read()
   idx = content.find("# MARKER")
   print(repr(content[idx:idx+400]))
   ```
3. **Copy the EXACT text** (whitespace, quotes, indentation) into your old_string
4. **Craft the exact replacement** — write the correct code with proper indentation
5. **Call `patch`** with precise multi-line old_string and new_string

**Key trick**: use `read_file` to see the actual file contents with line numbers, then copy-paste those exact lines (including the line numbers' content) into your old_string. Do NOT guess the indentation — copy from the terminal output.

### Option C: Delete-and-insert (when old_string is too long or fragile)

If the garbage block is so long or has such weird characters that matching it is error-prone:

1. Read the file completely
2. Use a Python script to find-and-replace:
   ```python
   with open("file.py") as f:
       content = f.read()
   old = "garbage block"
   new = "correct code"
   content = content.replace(old, new)
   with open("file.py", "w") as f:
       f.write(content)
   ```
3. Then syntax-check:
   ```bash
   python3 -c "import py_compile; py_compile.compile('file.py', doraise=True)"
   ```

## Pitfalls

- **`patch` NEVER matches across very long old_strings containing exact file content with weird whitespace** — the fuzzy matcher may silently choose a different match location. Use a Python script (`content.replace()`) instead for long blocks.
- **Always verify with `python3 -c "import py_compile"`** after the fix — syntax check catches orphaned code like `for d in details:\n    }`.
- **If patch succeeds (reports "1 occurrence") but you see no diff in the expected area**, the fuzzy matcher matched a completely different location. Read the diff output carefully.
- **After fixing, restart the server and curl-test the actual endpoint** — don't just syntax-check. The garbled function may have left side effects (e.g. a dangling `cur` variable in module scope).
