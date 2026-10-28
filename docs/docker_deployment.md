# Local Docker deployment

The Compose project is named `roadscope`. Both services use `roadscope:local`, built from Python 3.13 with the pinned inference/dashboard dependencies in `requirements-runtime.txt`. Training, MLflow and test dependencies remain outside the runtime image. Raw inputs and model training are not performed at container startup.

## Start

Start Docker Desktop and wait until `docker version` shows a Linux server, then open a terminal in the extracted project folder:

```powershell
docker compose config --quiet
docker compose up --build -d --wait --wait-timeout 180
python scripts/verify_deployment.py
python scripts/verify_dashboard_api.py
```

- Dashboard: http://localhost:8501
- FastAPI interactive documentation: http://localhost:8000/docs
- API readiness: http://localhost:8000/health

The existing host Streamlit session on port 8502 is independent. The container dashboard is on port 8501. Host ports are bound to loopback; no public hosting or registry push is involved.

The dashboard prediction form calls `http://api:8000/predict` over the Compose network. Compose sets `TRAFFIC_API_URL` and waits for API readiness before starting the dashboard. Local non-Docker runs default to `http://127.0.0.1:8000` and require starting uvicorn separately. A failed API request displays an error; the dashboard does not run the model locally.

## Data and model mounts

| Host folder | Container path | Access |
|---|---|---|
| `data/processed` | `/opt/traffic/data/processed` | Dashboard, read only |
| `models` | `/opt/traffic/models` | Both services, read only |
| `logs` | `/opt/traffic/logs` | API telemetry, read/write |

Keep the included processed artifacts and evaluated `models/severity.joblib` in place. The image runs as user `traffic` (UID 10001); the logs bind mount must be writable by that user on Linux hosts. Docker Desktop provides the Windows bind mounts. Inference is conditional collision-severity classification, not collision occurrence prediction.

## Verification and evidence

`scripts/verify_deployment.py` requires two healthy containers, checks Streamlit's health endpoint, confirms API readiness and the evaluated model version, sends a valid scenario, verifies normalized probabilities and checks an invalid request returns HTTP 422. It writes the result, container image IDs, port mappings and timestamp to `docs/evidence/deployment/docker_verification.json`.

The dashboard health check verifies the HTTP server. A separate browser check confirms that processed data actually renders in the application. Build/start output is retained in `logs/docker_deployment.log`. Historical evidence is not a guarantee that containers remain running after shutdown.

`scripts/verify_dashboard_api.py` exercises the actual Streamlit form inside the dashboard container, checks the returned prediction and model-version caption, and confirms a successful new request in the API telemetry. Evidence is saved in `docs/evidence/deployment/dashboard_api_verification.json`.

```powershell
docker compose ps
docker compose logs --tail 100 api dashboard
docker compose restart
docker compose stop
docker compose start --wait
```

To remove this project's containers and network while retaining bind-mounted data/model/log folders, run `docker compose down`. Changes to Python code or runtime requirements require `docker compose up --build -d --wait`; model-file replacement requires service restart after approval. Container restart policy is `unless-stopped` and requires Docker Desktop itself to be running.

## Troubleshooting

If the CLI reports `Docker Desktop is unable to start`, verify WSL with `wsl --version`. During this deployment Docker had cached a precondition failure from before WSL installation; `docker desktop restart` allowed it to detect WSL and bring up its Linux engine. A separate Ubuntu distribution was not needed. See the official backend documentation: https://docs.docker.com/desktop/features/wsl/ .

If ports 8000/8501 are already occupied, stop the conflicting service or adjust both the host port mapping and the verifier's host URLs. Do not change health-check container ports. If the API reports a missing model, confirm `models/severity.joblib` is present before starting; a running process alone does not satisfy the API readiness check.
