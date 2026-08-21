"""FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.config import settings
from apps.api.gateway import GatewayMiddleware, get_request_id, register_exception_handlers
from apps.api.gateway.errors import structured_error
from apps.api.routers import (
    actions,
    agent_roles,
    agents,
    approvals,
    audit,
    auth,
    health,
    intelligence,
    policies,
    scenarios,
    verifications,
)
from apps.api.state import state

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_production_safety()
    logger.info(
        "Starting OpenWorld API",
        demo_mode=settings.demo_mode,
        production=settings.is_production,
    )
    state.init_database()
    state.load_demo_data()
    if settings.demo_mode:
        await _seed_demo_actions()
    yield
    logger.info("Shutting down OpenWorld API")


async def _seed_demo_actions():
    """Seed deterministic demo actions once (idempotent on restart)."""
    if state.list_actions(limit=1):
        return

    agent = next(a for a in state.list_agents() if a.name == "EmailBot")
    action = state.lifecycle.create_action(
        agent_id=agent.id,
        agent_name=agent.name,
        action="email.send",
        target="user@example.com",
        parameters={"to": "user@example.com", "subject": "Welcome to OpenWorld"},
    )
    result = await state.lifecycle.process(action, agent=agent, auto_approve=True)
    state.save_action(result)

    agent = next(a for a in state.list_agents() if a.name == "FinanceBot")
    action = state.lifecycle.create_action(
        agent_id=agent.id,
        agent_name=agent.name,
        action="payment.create",
        target="vendor@corp.com",
        parameters={"amount": 600000, "recipient": "Vendor Corp"},
    )
    result = await state.lifecycle.process(action, agent=agent)
    state.save_action(result)

    action = state.lifecycle.create_action(
        agent_id=agent.id,
        agent_name=agent.name,
        action="payment.create",
        target="ABC Services",
        parameters={"amount": 75000, "recipient": "ABC Services", "reason": "Monthly invoice"},
    )
    result = await state.lifecycle.process(action, agent=agent)
    state.save_action(result, approval_status="pending")

    agent = next(a for a in state.list_agents() if a.name == "InvoiceBot")
    action = state.lifecycle.create_action(
        agent_id=agent.id,
        agent_name=agent.name,
        action="invoice.send",
        target="client@acme.com",
        parameters={"invoice_id": "INV-1001", "amount": 25000},
    )
    result = await state.lifecycle.process(action, agent=agent, auto_approve=True)
    state.save_action(result)


app = FastAPI(
    title="OpenWorld API",
    description="The Trust Layer for the Agentic Internet",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    GatewayMiddleware,
    max_body_bytes=settings.max_request_bytes,
    max_response_bytes=settings.max_response_bytes,
)

register_exception_handlers(app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = get_request_id(request)
    logger.error("Unhandled exception", error=str(exc), request_id=request_id)
    return JSONResponse(
        status_code=500,
        content=structured_error(
            status_code=500,
            message="Please try again or contact support",
            request_id=request_id,
        ),
        headers={"X-Request-ID": request_id},
    )


app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(agent_roles.router, prefix="/api/v1/agents", tags=["Agent Roles"])
app.include_router(actions.router, prefix="/api/v1/actions", tags=["Actions"])
app.include_router(policies.router, prefix="/api/v1/policies", tags=["Policies"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["Approvals"])
app.include_router(verifications.router, prefix="/api/v1/verifications", tags=["Verifications"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])
app.include_router(scenarios.router, prefix="/api/v1", tags=["Scenarios"])
app.include_router(intelligence.router, prefix="/api/v1/intelligence", tags=["Intelligence"])
