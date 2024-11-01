import pytest
import asyncio
import trio
from websockets import serve


@pytest.fixture(scope="session", autouse=True)
def start_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def websocket_handler(websocket, path):
        async for message in websocket:
            await websocket.send(message)

    server = loop.run_until_complete(serve(websocket_handler, "127.0.0.1", 8000))
    yield
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()


@pytest.fixture
def asyncio_event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def trio_event_loop():
    yield trio.open_memory_channel(0)