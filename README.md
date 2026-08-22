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

Instead of trusting an agent directly, OpenWorld evaluates every action through a deterministic trust pipeline covering:

**Identity → Capability → Policy → Risk → Approval → Execution → Verification → Audit**

### Core Principle

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

The hosted environment demonstrates the OpenWorld trust architecture and command center.

External actions such as email delivery, payments, webhooks, and similar integrations remain **sandbox/demo operations** unless an explicit production connector is configured.

No real customer systems or financial transactions are enabled by default.

---

# Why OpenWorld?

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

The more important question becomes:

> **"Should the AI be allowed to perform this action?"**

OpenWorld addresses this problem by placing a **deterministic trust boundary** between an AI agent and the systems it wants to control.

```text
AI Agent
   │
   ▼
OpenWorld Gateway
   │
   ├── Identity
   ├── Capabilities
   ├── Policy
   ├── Risk
   ├── Decision
   ├── Approval
   ├── Execution
   ├── Verification
   └── Audit
          │
          ▼
     Target System
