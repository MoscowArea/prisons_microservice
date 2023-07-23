from fastapi import FastAPI

from presentation.presentation import router


def setup_routers(app: FastAPI):
    app.include_router(router)
