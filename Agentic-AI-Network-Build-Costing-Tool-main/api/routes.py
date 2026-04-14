"""API routes for FTTP estimator."""
import asyncio
import re
from datetime import datetime
from typing import Any, Optional

import bcrypt
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from pydantic import BaseModel

from api.schemas import (
    CostEstimationInput,
    BudgetPlanningInput,
    UpgradePlannerInput,
    MapsPlannerInput,
)
from db import get_db
from db.models import EstimationResult, ProjectDocument
from graph import run_estimation_graph, run_budget_graph, run_upgrade_graph, run_maps_graph
from agents.ollama_client import is_ollama_available
from config import get_settings
from config.currency import apply_currency_to_result, CURRENCY_RATES

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


class SignupBody(BaseModel):
    email: str
    password: str


class LoginBody(BaseModel):
    email: str
    password: str


@router.post("/auth/signup")
async def api_signup(body: SignupBody):
    """Register a new user; credentials are stored in MongoDB `users` collection."""
    email = body.email.strip().lower()
    if not email or not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    db = await get_db()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already registered")
    doc = {
        "email": email,
        "password_hash": _hash_password(body.password),
        "created_at": datetime.utcnow(),
    }
    ins = await db.users.insert_one(doc)
    return {"user_id": str(ins.inserted_id), "email": email}


@router.post("/auth/login")
async def api_login(body: LoginBody):
    """Verify email/password against MongoDB and return user id for the app."""
    email = body.email.strip().lower()
    db = await get_db()
    user = await db.users.find_one({"email": email})
    if not user or not _verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"user_id": str(user["_id"]), "email": user["email"]}


@router.get("/auth/me")
async def api_auth_me(user_id: str):
    """Return email for a user id (hydrates header when localStorage has no email)."""
    db = await get_db()
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    user = await db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user_id, "email": user.get("email", "")}


@router.get("/config/maps")
async def api_maps_config():
    """Return Google Maps API key for frontend (empty if not set)."""
    from config import get_settings
    s = get_settings()
    return {"google_maps_api_key": s.google_maps_api_key or ""}


@router.get("/ollama-status")
async def api_ollama_status():
    """Check if Ollama is running. When false, app still works but uses fallback text for explanations."""
    available = is_ollama_available()
    s = get_settings()
    return {
        "available": available,
        "message": "Ollama is running. AI explanations are enabled."
        if available
        else f"Ollama is not running at {s.ollama_base_url}. Start with: ollama serve. Then: ollama pull {s.ollama_model}. Cost estimates still work.",
    }


def _input_to_dict(model: Any) -> dict:
    return model.model_dump(exclude_none=True)


def _result_to_estimation_result(data: dict) -> EstimationResult:
    return EstimationResult(
        total_cost=data.get("total_cost", 0),
        cost_breakdown=data.get("cost_breakdown", {}),
        quantities=data.get("quantities", {}),
        roi=data.get("roi"),
        payback_period_months=data.get("payback_period_months"),
        annual_revenue=data.get("annual_revenue"),
        annual_opex=data.get("annual_opex"),
        net_annual=data.get("net_annual"),
        roi_payback_explanation=data.get("roi_payback_explanation"),
        llm_explanation=data.get("llm_explanation", ""),
        deployment_strategy=data.get("deployment_strategy", ""),
        optimization_suggestions=data.get("optimization_suggestions", []),
        architecture_type=data.get("architecture_type"),
        error_margin=data.get("error_margin"),
        charts_data=data.get("charts_data"),
        currency=data.get("currency"),
        currency_symbol=data.get("currency_symbol"),
    )


@router.post("/estimate/cost")
async def api_cost_estimation(body: CostEstimationInput):
    """Run cost estimation (Option 1)."""
    inputs = _input_to_dict(body)
    inputs["area_name"] = inputs.get("area_name") or inputs.get("area_code") or "Area"
    inputs.pop("currency", None)  # remove from inputs, use body.currency
    currency = (body.currency or "INR").upper()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_estimation_graph, inputs)
    if not result:
        raise HTTPException(status_code=500, detail="Estimation failed")
    return apply_currency_to_result(result, currency)


@router.post("/estimate/budget")
async def api_budget_planning(body: BudgetPlanningInput):
    """Run budget-based planning (Option 2). Budget in selected currency; result in same."""
    inputs = _input_to_dict(body)
    inputs.pop("currency", None)
    currency = (body.currency or "INR").upper()
    rate = CURRENCY_RATES.get(currency, 1.0)
    if rate and rate != 1.0:
        inputs["budget"] = float(inputs.get("budget", 0)) / rate
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_budget_graph, inputs)
    if not result:
        raise HTTPException(status_code=500, detail="Budget planning failed")
    return apply_currency_to_result(result, currency)


@router.post("/estimate/upgrade")
async def api_upgrade_planner(body: UpgradePlannerInput):
    """Run upgrade planner (Option 3)."""
    inputs = _input_to_dict(body)
    inputs["current_premises"] = body.current_capacity
    inputs["target_premises"] = body.target_capacity
    inputs.pop("currency", None)
    currency = (body.currency or "INR").upper()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_upgrade_graph, inputs)
    if not result:
        raise HTTPException(status_code=500, detail="Upgrade planning failed")
    return apply_currency_to_result(result, currency)


@router.post("/maps/estimate")
async def api_maps_estimate(body: MapsPlannerInput):
    """Run maps planner: only target_location + total_premises; backend infers type, architecture, distance."""
    inputs = _input_to_dict(body)
    inputs["target_location"] = (body.target_location or "Area").strip() or "Area"
    inputs.pop("currency", None)
    currency = (body.currency or "INR").upper()
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_maps_graph, inputs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not result:
        raise HTTPException(status_code=500, detail="Maps estimation failed")
    return apply_currency_to_result(result, currency)


class SaveProjectBody(BaseModel):
    title: str = ""
    type: str
    inputs: dict
    result: dict
    user_id: str = "default"


@router.post("/projects/save")
async def api_save_project(body: SaveProjectBody):
    """Save estimation as project to MongoDB."""
    db = await get_db()
    est = _result_to_estimation_result(body.result)
    doc = {
        "user_id": body.user_id,
        "type": body.type,
        "title": body.title or f"{body.type} - {datetime.utcnow().isoformat()[:19]}",
        "inputs": body.inputs,
        "result": est.model_dump(),
        "created_at": datetime.utcnow(),
    }
    ins = await db.projects.insert_one(doc)
    doc["id"] = str(ins.inserted_id)
    return {"id": doc["id"], "title": doc["title"]}


@router.get("/projects")
async def api_list_projects(user_id: str = "default", limit: int = 100):
    """List saved projects."""
    db = await get_db()
    cursor = db.projects.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    items = []
    async for d in cursor:
        d["id"] = str(d.pop("_id"))
        items.append(d)
    return {"projects": items}


@router.get("/projects/{project_id}")
async def api_get_project(project_id: str):
    """Get one project by ID."""
    db = await get_db()
    try:
        obj = await db.projects.find_one({"_id": ObjectId(project_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")
    obj["id"] = str(obj.pop("_id"))
    return obj


@router.delete("/projects/{project_id}")
async def api_delete_project(project_id: str):
    """Delete a project."""
    db = await get_db()
    try:
        res = await db.projects.delete_one({"_id": ObjectId(project_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": project_id}
