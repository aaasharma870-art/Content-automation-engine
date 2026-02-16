# Content Engine V1.2 Runbook

## 1. Prerequisites
- **Docker Desktop**: Must be installed and running.
- **Python 3.10+**: For running the test script.

## 2. Configuration (`.env`)
You need to set up your API keys.
1.  Copy the example:
    ```bash
    copy .env.example .env
    ```
2.  Open `.env` and fill in:
    - `OPENAI_API_KEY`: Required for the Writer/Brain.
    - `POSTGRES_PASSWORD`: Set a secure password.
    - `REDIS_HOST`: Set to `localhost` if running script locally, or `redis` if inside Docker.

## 3. Starting the Stack
The system runs in Docker containers.

```bash
cd infra
docker-compose up --build -d
```

**Check Status**:
- **Brain Service**: `http://localhost:8000/docs`
- **Render Service**: `http://localhost:8001/docs` (if port mapped)
- **n8n**: `http://localhost:5678`

## 4. Running a Test Job
I have included a script `run_test_job.py` to trigger the Brain manually.

```bash
# Install requests if needed
pip install requests

# Run the test
python run_test_job.py
```

### What happens?
1.  The script sends a `POST /generate/job` to the **Brain**.
2.  The **Brain** calls:
    - **Collector**: Gets a topic.
    - **Ranker**: Scores it.
    - **Writer**: Writes the script.
    - **Art Director**: Picks music/visuals.
3.  The **Brain** returns a full `JobSpec` JSON.
4.  The script then sends this `JobSpec` to the **Renderer**.
5.  The **Renderer** generates the FFmpeg command (and prints it).

## 5. Next Steps (Production)
Once you verify the endpoints work:
1.  **Uncomment Execution**: In `services/render/main.py`, uncomment the `subprocess.run(cmd)` line to actually generate video files.
2.  **n8n Automation**:
    - Open `http://localhost:5678`.
    - Create a workflow that runs daily.
    - Add an **HTTP Request** node to POST to `http://brain:8000/generate/job`.
3.  **Deploy**: Push this code to a VPS (DigitalOcean/AWS) and run `docker-compose up -d`.
