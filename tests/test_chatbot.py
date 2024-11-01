# tests/test_chatbot.py

import pytest
import subprocess
import asyncio
import websockets
import socket
import json
import os
import time
import requests

HOST = "127.0.0.1"
EVALUATION_FOLDER = "tests/evaluation"
OUTPUT_FILE = os.path.join(EVALUATION_FOLDER, "results.jsonl")
QUESTIONS_FILE = os.path.join("tests", "questions.jsonl")
HEALTH_ENDPOINT = "/health"  # Ensure your FastAPI app has a health endpoint


def find_free_port():
    """Finds a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def wait_for_server(host, port, endpoint="/"):
    """Wait for the server to start by polling the health endpoint."""
    url = f"http://{host}:{port}{endpoint}"
    timeout = 10  # seconds
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
    """Starts the FastAPI server as a subprocess."""
    port = find_free_port()

    # Start FastAPI server
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

    # Terminate the server after tests
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


@pytest.mark.asyncio
async def test_send_questions_and_collect_responses(start_server):
    port = start_server
    uri = f"ws://{HOST}:{port}/chat"

    # Ensure evaluation folder exists
    os.makedirs(EVALUATION_FOLDER, exist_ok=True)

    # Read questions from questions.jsonl
    with open(QUESTIONS_FILE, "r") as f:
        questions = [json.loads(line) for line in f if line.strip()]

    # Open the output file in write mode to write results immediately
    with open(OUTPUT_FILE, "w") as outfile:
        async with websockets.connect(uri) as websocket:
            for q in questions:
                question = q.get("question")
                await websocket.send(question)

                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                except asyncio.TimeoutError:
                    pytest.fail(f"Timeout while waiting for response to: {question}")

                assert (
                    response is not None
                ), f"No response received for question: {question}"

                print(f"Question: {question}")
                print(f"Response: {response}")

                # Write question and response to the output file and flush immediately
                result = {"question": question, "response": response}
                outfile.write(json.dumps(result) + "\n")
                outfile.flush()


if __name__ == "__main__":
    pytest.main(["-s", "tests/test_chatbot.py"])
