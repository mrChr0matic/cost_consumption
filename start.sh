# start.sh
#!/bin/bash
set -e

# Run FastAPI on 8000 (internal, called by streamlit directly)
uvicorn entrypoint:app --host 127.0.0.1 --port 8051 &

# Run Streamlit on the externally exposed port
streamlit run streamlit_app.py \
  --server.port 8000 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false