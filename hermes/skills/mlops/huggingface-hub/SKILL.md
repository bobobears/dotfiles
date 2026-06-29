---
name: huggingface-hub
description: "HuggingFace hf CLI: search/download/upload models, datasets."
version: 1.0.0
author: Hugging Face
license: MIT
tags: [huggingface, hf, models, datasets, hub, mlops]
platforms: [linux, macos, windows]
---

# Hugging Face CLI (`hf`) Reference Guide

The `hf` command is the modern command-line interface for interacting with the Hugging Face Hub, providing tools to manage repositories, models, datasets, and Spaces.

> **IMPORTANT:** The `hf` command replaces the now deprecated `huggingface-cli` command.

## Quick Start
*   **Installation:** `curl -LsSf https://hf.co/cli/install.sh | bash -s`
*   **Help:** Use `hf --help` to view all available functions and real-world examples.
*   **Authentication:** Recommended via `HF_TOKEN` environment variable or the `--token` flag.

---

## Core Commands

### General Operations
*   `hf download REPO_ID`: Download files from the Hub.
*   `hf upload REPO_ID`: Upload files/folders (recommended for single-commit).
*   `hf upload-large-folder REPO_ID LOCAL_PATH`: Recommended for resumable uploads of large directories.
*   `hf sync`: Sync files between a local directory and a bucket.
*   `hf env` / `hf version`: View environment and version details.

### Authentication (`hf auth`)
*   `login` / `logout`: Manage sessions using tokens from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
*   `list` / `switch`: Manage and toggle between multiple stored access tokens.
*   `whoami`: Identify the currently logged-in account.

### Repository Management (`hf repos`)
*   `create` / `delete`: Create or permanently remove repositories.
*   `duplicate`: Clone a model, dataset, or Space to a new ID.
*   `move`: Transfer a repository between namespaces.
*   `branch` / `tag`: Manage Git-like references.
*   `delete-files`: Remove specific files using patterns.

---

## Specialized Hub Interactions

### Datasets & Models
*   **Datasets:** `hf datasets list`, `info`, and `parquet` (list parquet URLs).
*   **SQL Queries:** `hf datasets sql SQL` — Execute raw SQL via DuckDB against dataset parquet URLs.
*   **Models:** `hf models list` and `info`.
*   **Papers:** `hf papers list` — View daily papers.

### Discussions & Pull Requests (`hf discussions`)
*   Manage the lifecycle of Hub contributions: `list`, `create`, `info`, `comment`, `close`, `reopen`, and `rename`.
*   `diff`: View changes in a PR.
*   `merge`: Finalize pull requests.

### Infrastructure & Compute
*   **Endpoints:** Deploy and manage Inference Endpoints (`deploy`, `pause`, `resume`, `scale-to-zero`, `catalog`).
*   **Jobs:** Run compute tasks on HF infrastructure. Includes `hf jobs uv` for running Python scripts with inline dependencies and `stats` for resource monitoring.
*   **Spaces:** Manage interactive apps. Includes `dev-mode` and `hot-reload` for Python files without full restarts.

### Storage & Automation
*   **Buckets:** Full S3-like bucket management (`create`, `cp`, `mv`, `rm`, `sync`).
### Large File Downloads via aria2c (Recommended for Assets >5 GB)

The `hf download` command uses single-stream HTTP and can time out on large GGUF files (5+ GB). For reliable large-file downloads, use `aria2c` with multi-threaded connections against the hf-mirror:

```bash
aria2c -x 4 -s 4 --continue=true \
  --header="User-Agent: huggingface-hub/1.21.0" \
  -o "<filename.gguf>" \
  "https://hf-mirror.com/<user>/<model>/resolve/main/<filename.gguf>"
```

Parameters:
- `-x 4` / `-s 4`: 4 parallel connections (adjust up to 16 for very large repos)
- `--continue=true`: resume interrupted downloads
- The URL is the standard hf-mirror resolve URL — aria2c follows the 302 redirect to the CDN automatically

Run `aria2c` as a background terminal process while working on other tasks. Check progress with `ls -lh <filename>` or `process(action='poll')` in Hermes.
*   **Webhooks:** Automate workflows by managing Hub webhooks (`create`, `watch`, `enable`/`disable`).
*   **Collections:** Organize Hub items into collections (`add-item`, `update`, `list`).

---

## Advanced Usage & Tips

### Global Flags
*   `--format json`: Produces machine-readable output for automation.
*   `-q` / `--quiet`: Limits output to IDs only.

### Extensions & Skills
*   **Extensions:** Extend CLI functionality via GitHub repositories using `hf extensions install REPO_ID`.
*   **Skills:** Manage AI assistant skills with `hf skills add`.
