"""
CutFlow System Router — Supported LLMs, models, and storage maintenance endpoints.
"""

from fastapi import APIRouter
from cutflow.services.storage import get_storage_stats, cleanup_storage

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/storage/info")
async def get_storage_info():
    """Return storage usage information."""
    return get_storage_stats()


@router.post("/storage/cleanup")
async def manual_cleanup(keep_recent: int = 1):
    """Purge all non-recent uploads and project files immediately."""
    cleanup_storage(max_age_hours=0.01, keep_latest_uploads=keep_recent)
    return {"status": "success", "stats": get_storage_stats()}


@router.get("/models")
async def get_supported_models():
    """Return supported LLM providers and models."""
    return {
        "providers": [
            {
                "id": "groq",
                "name": "Groq (Ultra-Fast LPU Inference)",
                "recommended": True,
                "docs_url": "https://console.groq.com/docs/models",
                "models": [
                    {
                        "id": "openai/gpt-oss-120b",
                        "name": "OpenAI GPT-OSS 120B",
                        "description": "Recommended. Flagship 120B parameter OpenAI model on Groq. Deep reasoning & exact JSON.",
                        "context_window": 128000,
                    },
                    {
                        "id": "openai/gpt-oss-20b",
                        "name": "OpenAI GPT-OSS 20B",
                        "description": "Fast 20B parameter OpenAI open model on Groq.",
                        "context_window": 32768,
                    },
                    {
                        "id": "qwen/qwen3.6-27b",
                        "name": "Qwen 3.6 27B",
                        "description": "Multimodal capable high-speed model on Groq.",
                        "context_window": 32768,
                    },
                    {
                        "id": "groq/compound",
                        "name": "Groq Compound",
                        "description": "Groq compound reasoning system.",
                        "context_window": 128000,
                    },
                    {
                        "id": "groq/compound-mini",
                        "name": "Groq Compound Mini",
                        "description": "Compact Groq compound system.",
                        "context_window": 128000,
                    },
                ],
            },
            {
                "id": "gemini",
                "name": "Google Gemini",
                "recommended": False,
                "docs_url": "https://ai.google.dev/gemini-api/docs/models",
                "models": [
                    {
                        "id": "gemini-2.0-flash",
                        "name": "Gemini 2.0 Flash",
                        "description": "Fast and intelligent next-gen model.",
                        "context_window": 1000000,
                    },
                    {
                        "id": "gemini-1.5-flash",
                        "name": "Gemini 1.5 Flash",
                        "description": "Cost-efficient high-speed model.",
                        "context_window": 1000000,
                    },
                    {
                        "id": "gemini-1.5-pro",
                        "name": "Gemini 1.5 Pro",
                        "description": "Maximum reasoning capability.",
                        "context_window": 2000000,
                    },
                ],
            },
        ]
    }
