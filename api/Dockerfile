# Lab 10 — backend Dockerfile.
#
# Build context is the repo root (parent of api/) — see docker-compose.yml
# (`context: .`, `dockerfile: api/Dockerfile`) and the CI docker job
# (`docker build -f api/Dockerfile .`). Running `uvicorn api.main:app`
# from /app preserves the starter's package-relative imports
# (`from .deps import ...`); `cd api && uvicorn main:app` would break them.
FROM python:3.11-slim

WORKDIR /app

# Cache-friendly layer order: install requirements before copying the
# rest of the source so a code change does not bust the pip layer.
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install the spaCy English model needed by /extract. `spacy download`
# builds a malformed URL (.../download/-en_core_web_sm/-...tar.gz → 404) on
# some spaCy/pip combos, so fall back to the pinned wheel when it fails.
RUN python -m spacy download en_core_web_sm \
    || pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

# Copy the rest of the build context (the api/ package lands at /app/api/).
COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
