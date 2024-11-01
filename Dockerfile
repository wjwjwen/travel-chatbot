FROM python:3.11

WORKDIR /code

COPY . .

RUN pip install --no-cache-dir --upgrade -r backend/requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable
ENV PORT 8000


CMD ["uvicorn", "backend.app:app","--host", "0.0.0.0", "--port", "8000"]