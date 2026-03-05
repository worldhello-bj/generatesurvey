from routers.questionnaire import router as questionnaire_router
from routers.generate import router as generate_router
from routers.download import router as download_router
from routers.admin import router as admin_router

__all__ = ["questionnaire_router", "generate_router", "download_router", "admin_router"]
