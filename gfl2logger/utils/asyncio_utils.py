import asyncio
from collections.abc import Coroutine

from mitmproxy.utils import asyncio_utils


def create_task(coro: Coroutine) -> asyncio.Task:
    return asyncio_utils.create_task(coro, name=coro.__qualname__, keep_ref=True)
