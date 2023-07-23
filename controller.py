import inspect
import json
import logging
import uuid
from typing import TypeVar, Callable, Coroutine, AsyncContextManager, Any

import nats
from nats.aio.msg import Msg
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database import Prison
from dto import ResponseModel, Form, Request, PrisonResponse, RequestModel, ErrorModel

TBaseModel = TypeVar("TBaseModel", bound=BaseModel)

HandlerType = Callable[[..., TBaseModel], Coroutine[None, None, bytes | None]]


class NatsController:
    def __init__(self, nc: nats.NATS, local_session: Callable[[], AsyncContextManager[AsyncSession]],
                 scheme: Form) -> None:
        self.nc = nc
        self.local_session = local_session
        self.scheme = scheme
        self.logger = logging.getLogger(self.__class__.__name__)

    async def setup_routes(self, config: Config) -> None:
        js = self.nc.jetstream()

        await js.add_stream(
            name="form_scheme_stream", subjects=["scheme", "scheme.>"]
        )
        await js.add_stream(
            name="form_data_stream", subjects=["data", "data.>"]
        )

        await js.subscribe(f"scheme.{self.scheme.name}",
                           cb=self.message_handler(self.get_scheme_by_name), durable="form_data_prisons_s_scheme")
        await js.subscribe(f"scheme", cb=self.message_handler(self.get_scheme),
                           durable="form_data_prisons_scheme")
        await js.subscribe(f"data.{self.scheme.name}", cb=self.message_handler(self.get_all_data),
                           durable="form_data_prisons_all")

        await js.subscribe(f"data.{self.scheme.name}.create", cb=self.message_handler(self.create_data),
                           durable="form_data_prisons_create")

    def message_handler(
            self, handler: HandlerType
    ) -> Callable[[Msg], Coroutine[None, None, None]]:
        signature = inspect.signature(handler)
        message_type = signature.parameters.get('data')

        def parse_message(msg: Msg) -> dict[str, Any] | None:
            parsed_message = {"req_id": msg.headers['req_id']}
            if message_type is not None:
                self.logger.debug(json.loads(msg.data.decode("utf-8")))
                parsed_message[message_type.name] = Request[message_type.annotation].model_validate_json(
                    msg.data).data
            return parsed_message

        async def wrapper(msg: Msg) -> None:
            try:
                self.logger.debug(f"received message: {msg.data=} - {msg.headers=} - {handler.__name__}")
                await handler(**parse_message(msg))
                await msg.ack()
            except ValidationError as e:
                self.logger.error(f"validation exception: {e}")
                await self.nc.jetstream().publish(
                    f"data.{self.scheme.name}.{msg.headers['req_id']}",
                    ResponseModel[ErrorModel](
                        status_code=422,
                        data=ErrorModel(detail="Invalid request data"),
                    )
                    .model_dump_json()
                    .encode("utf-8")
                )
                await msg.ack()

        return wrapper

    async def get_all_data(self, req_id: str) -> None:
        async with self.local_session() as session:
            form_data = (await session.scalars(
                select(Prison)
            )).fetchall()
            await self.nc.jetstream().publish(
                f"data.{req_id}",
                payload=ResponseModel[list[PrisonResponse]](status_code=200,
                                                            data=[PrisonResponse.model_validate(d) for d in
                                                                  form_data]).model_dump_json().encode("utf-8")
            )
            self.logger.debug(f"Sent: {len(form_data)}")

    async def create_data(self, req_id: str, data: RequestModel) -> None:
        async with self.local_session() as session:
            try:
                new_data = Prison()
                new_data.id = uuid.uuid4()
                new_data.name_ru = data.name_ru
                new_data.name_ua = data.name_ua
                new_data.subject = data.subject
                new_data.object_type = data.object_type
                new_data.lat = data.lat
                new_data.lon = data.lon
                new_data.address = data.address
                new_data.management = data.management
                new_data.employees_count = data.employees_count
                new_data.prisoners_count = data.prisoners_count
                new_data.staff = data.staff
                new_data.contacts = data.contacts

                session.add(new_data)
                await session.commit()
                self.logger.info(f"Added new data: {new_data.name_ru}")
            except AttributeError as e:
                self.logger.error(e)
                await self.nc.jetstream().publish(
                    f"data.{self.scheme.name}.{req_id}",
                    payload=ResponseModel(status_code=500, data=ErrorModel(detail=str(e))).model_dump_json().encode(
                        "utf")
                )
            except IntegrityError as e:
                self.logger.error(e)
                await self.nc.jetstream().publish(
                    f"data.{self.scheme.name}.{req_id}",
                    payload=ResponseModel(status_code=422, data=ErrorModel(detail=str(e))).model_dump_json().encode(
                        "utf")
                )

    async def get_scheme(self, req_id: str) -> None:
        await self.nc.jetstream().publish(f"scheme.{req_id}",
                                          payload=self.scheme.model_dump_json().encode("utf-8"))

    async def get_scheme_by_name(self, req_id: str) -> None:
        await self.nc.jetstream().publish(f"scheme.{req_id}",
                                          payload=self.scheme.model_dump_json().encode("utf-8"))
