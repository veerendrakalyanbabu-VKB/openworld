# OpenWorld

[![Live Demo](https://img.shields.io/badge/Live%20Demo-OpenWorld-success?style=for-the-badge)](https://openworld-web.onrender.com/)
[![API Health](https://img.shields.io/badge/API-Healthy-success?style=for-the-badge)](https://openworld-api.onrender.com/api/v1/health)
[![Release](https://img.shields.io/github/v/release/veerendrakalyanbabu-VKB/openworld?style=flat-square)](https://github.com/veerendrakalyanbabu-VKB/openworld/releases)
[![License](https://img.shields.io/github/license/veerendrakalyanbabu-VKB/openworld?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-Next.js-blue?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)
[![Tests](https://img.shields.io/badge/Tests-197%20passing-success?style=flat-square)](#testing)
[![Status](https://img.shields.io/badge/Status-Early%20Developer%20Preview-orange?style=flat-square)](#project-status)

> **Human Intent. Machine Execution. Verifiable Results.**

OpenWorld is a developer-first **trust and execution layer for AI agents**.

It provides a controlled boundary between what an AI agent **wants to do** and what a system is actually **allowed to execute**.

Instead of trusting an agent directly, OpenWorld evaluates every action through a deterministic trust pipeline:

**Identity → Capability → Policy → Risk → Approval → Execution → Verification → Audit**

## Core Principle

> **Never trust the agent. Verify the action.**

---

## 🚀 Live Preview

OpenWorld is publicly deployed and available as a hosted developer preview.

| Resource | Status |
|---|---|
| 🌐 **Command Center** | [Open OpenWorld](https://openworld-web.onrender.com/) |
| 🔌 **API** | [Open API](https://openworld-api.onrender.com/) |
| ❤️ **API Health** | [Check Health](https://openworld-api.onrender.com/api/v1/health) |
| 📦 **Source Code** | [GitHub Repository](https://github.com/veerendrakalyanbabu-VKB/openworld) |
| 🏷️ **Latest Release** | [v0.1.0](https://github.com/veerendrakalyanbabu-VKB/openworld/releases/tag/v0.1.0) |
| 🗄️ **Database** | PostgreSQL |
| ☁️ **Deployment** | Render |

### Hosted Preview Scope

The hosted environment demonstrates the OpenWorld trust architecture and Command Center.

External actions such as email delivery, payments, webhooks, and similar integrations remain **sandbox/demo operations** unless an explicit production connector is configured.

No real customer systems or financial transactions are enabled by default.

---

## Why OpenWorld?

AI agents are increasingly capable of taking actions:

- Sending emails
- Calling APIs
- Creating tickets
- Updating records
- Triggering workflows
- Moving data
- Initiating financial operations
- Interacting with cloud infrastructure

The problem is no longer only:

> **"Can the AI perform the task?"**

The more important question is:

> **"Should the AI be allowed to perform this action?"**

OpenWorld addresses this problem by placing a **deterministic trust boundary** between an AI agent and the systems it wants to control.

---

## 🏗️ Trust Architecture

---

## 🐍 Python SDK

OpenWorld provides a Python SDK for applications and AI agents that need to submit actions through the OpenWorld trust pipeline.

```python
from packages.sdk.openworld import OpenWorldClient

client = OpenWorldClient(
    base_url="http://localhost:8000",
)

result = client.actions.submit(
    agent_id="demo-agent",
    action_type="send_email",
    payload={
        "to": "developer@example.com",
        "subject": "OpenWorld test",
        "body": "Hello from OpenWorld",
    },
)

print(result)
```

The SDK provides a programmatic interface for submitting actions to OpenWorld. Every submitted action is evaluated through the trust boundary before execution.

**Identity → Capability → Policy → Risk → Approval → Execution → Verification → Audit**

This prevents an AI agent from bypassing OpenWorld and executing directly against a target system.

### SDK Responsibilities

The Python SDK supports:

- Action submission
- Action simulation
- Action status checks
- Authentication
- Approval workflows
- Policy access
- Audit access
- Correlation IDs
- Idempotency
- Structured API errors

For local development, the SDK can connect to:

```text
http://localhost:8000
```

For the hosted developer preview, configure the client with the deployed OpenWorld API URL.

> **Important:** External integrations remain sandbox/demo operations unless an explicitly configured production connector is enabled.

```text
                         AI Agent / SDK
                               │
                               ▼
                    ┌────────────────────┐
                    │  OpenWorld Gateway │
                    └─────────┬──────────┘
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
        Identity         Capability         Policy
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                            Risk
                              │
                              ▼
                           Decision
                              │
                       ┌──────┴──────┐
                       │             │
                    Approval      Rejected
                       │
                       ▼
                    Execution
                       │
                       ▼
                  Verification
                       │
                       ▼
                      Audit
                       │
                       ▼
                  Target System
