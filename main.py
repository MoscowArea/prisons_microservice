from __future__ import annotations

import asyncio
import logging

import nats
import uvicorn
from fastapi import FastAPI

from config import Config
from controller import NatsController
from database import setup_database
from presentation.setup import setup_routers

logger = logging.getLogger(__name__)


class Application:
    def __init__(self, app: FastAPI, config: Config):
        self.app = app
        self.config = config

    @classmethod
    async def from_config(cls, config: Config) -> Application:
        logging.basicConfig(level=logging.DEBUG)
        session, engine, form = await setup_database(config)
        nc = await nats.connect(servers=config.nats_servers)
        ctrl = NatsController(nc, session, form)
        await ctrl.setup_routes(config)

        fastapi_app = FastAPI()
        fastapi_app.state.db_session = session
        fastapi_app.state.form = lambda: form

        setup_routers(fastapi_app)

        return Application(fastapi_app, config)

    async def start_app(self) -> None:
        logger.info("HTTP server is starting")

        try:
            server = uvicorn.Server(
                config=uvicorn.Config(
                    app=self.app,
                    host=self.config.host,
                    port=int(self.config.port),
                )
            )
            await server.serve()
        except asyncio.CancelledError:
            logger.info("HTTP server has been interrupted")
        except BaseException as unexpected_error:
            logger.exception(f"HTTP server failed to start: {unexpected_error}")

    async def dispose(self) -> None:
        logger.info("Application is shutting down...")

        dispose_errors = []

        if len(dispose_errors) != 0:
            logger.error("Application has shut down with errors")

        logger.info("Application has successfully shut down")


async def main():
    config = Config()

    app = await Application.from_config(config)

    await app.start_app()


if __name__ == '__main__':
    asyncio.run(main())
