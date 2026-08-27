# Final Command Reference

Run backend commands from `backend/` after activating `.venv`.

| Task | Command |
| --- | --- |
| Activate backend environment | `.\.venv\Scripts\Activate.ps1` |
| Start backend | `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| Backend tests | `python -m unittest discover -s tests` |
| Import/OpenAPI check | `python -c "from app.main import app; print(len(app.openapi()['paths']))"` |
| Recommendation evaluation | `python scripts/evaluate_recommendations.py` |
| Index verification | `python scripts/verify_production_indexes.py` |
| Final pre-flight | `python scripts/final_preflight_check.py` |
| Final acceptance summary | `python scripts/final_acceptance_check.py` |
| Optional local smoke | `python scripts/production_smoke_test.py --base-url http://127.0.0.1:8000` |

Run frontend commands from `frontend/`.

| Task | Command |
| --- | --- |
| Start frontend | `npm run dev` |
| Frontend tests | `npm test` |
| TypeScript | `npx tsc --noEmit` |
| ESLint | `npm run lint` |
| Normal optimized build | `npm run build` |

PowerShell execution policy can block `npm.ps1`; `npm.cmd` and `npx.cmd` are
equivalent command shims when that occurs. No Docker command is required.
