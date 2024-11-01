import asyncio
import json
import os
import socket
import subprocess
import time
import timeit
from datetime import datetime

import pytest
import requests
import websockets

HOST = "127.0.0.1"
EVALUATION_FOLDER = "tests/evaluation"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = os.path.join(EVALUATION_FOLDER, f"results_{TIMESTAMP}.jsonl")
QUESTIONS_FILE = os.path.join("tests", "questions.jsonl")
HEALTH_ENDPOINT = "/health"


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def wait_for_server(host, port, endpoint="/"):
    url = f"http://{host}:{port}{endpoint}"
    timeout = 10
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Server did not start within {timeout} seconds.")


@pytest.fixture(scope="module", autouse=True)
def start_server():
    port = find_free_port()
    process = subprocess.Popen(
        ["uvicorn", "backend.app:app", "--host", HOST, "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        wait_for_server(HOST, port, HEALTH_ENDPOINT)
    except RuntimeError as e:
        process.terminate()
        process.wait()
        pytest.fail(str(e))

    yield port

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


async def send_and_receive(uri, question):
    async with websockets.connect(uri) as websocket:
        await websocket.send(question)
        start_time = timeit.default_timer()
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=90)
        except asyncio.TimeoutError:
            pytest.fail(f"Timeout while waiting for response to: {question}")
        end_time = timeit.default_timer()
        total_time = end_time - start_time
        assert response is not None, f"No response received for question: {question}"
        return {"question": question, "response": response, "time_taken": total_time}


@pytest.mark.asyncio
async def test_send_questions_and_collect_responses(start_server):
    port = start_server
    uri = f"ws://{HOST}:{port}/chat"

    os.makedirs(EVALUATION_FOLDER, exist_ok=True)

    with open(QUESTIONS_FILE, "r") as f:
        questions = [json.loads(line) for line in f if line.strip()]

    for question in questions:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = await send_and_receive(uri, question.get("question"))
            with open(OUTPUT_FILE, "a") as outfile:
                outfile.write(json.dumps(result) + "\n")
                outfile.flush()
        finally:
            loop.close()
