---
name: webhook-subscriptions
description: "Webhook subscriptions: event-driven agent runs."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [webhook, events, automation, integrations, notifications, push]
---

# Webhook Subscriptions

Create dynamic webhook subscriptions so external services (GitHub, GitLab, Stripe, CI/CD, IoT sensors, monitoring tools) can trigger Hermes agent runs by POSTing events to a URL.

## Setup (Required First)

```bash
hermes webhook list
```

If not enabled, enable with:
```bash
hermes webhook enable
```

## Creating a Subscription

```bash
# Basic subscription
hermes webhook subscribe --event issues --prompt "When a new issue is created, summarize it and respond"

# With skills
hermes webhook subscribe --event push --skills "github-code-review" --prompt "Review the pushed code changes"
```

## Management

```bash
# List subscriptions
hermes webhook list

# Delete a subscription
hermes webhook delete <id>

# Test a webhook
hermes webhook test <id>
```
