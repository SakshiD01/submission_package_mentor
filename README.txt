NOLHC Brexit ML Simulator - Mentor Submission Package
=====================================================

This is the reduced package for mentor evaluation.
It includes only the core implementation needed to run the project.

Included folders
----------------
1) experimenting_ml  -> Main runnable app (UI + inference API + model outputs)
2) nolhc_ml          -> Core ML utilities used by the inference stack

Quick run steps
---------------
1) Open terminal in this folder (submission_package_mentor).
2) Create virtual environment:
   python -m venv .venv

Fix for “python: command not found”

Create virtual environment:
- macOS/Linux:
    python3 -m venv .venv
    source .venv/bin/activate
- Windows (PowerShell):
    py -3 -m venv .venv
    .venv\Scripts\Activate.ps1


3) Activate:
   macOS/Linux:
   source .venv/bin/activate

   Windows PowerShell:
   .venv\Scripts\Activate.ps1

4) Install requirements:
   pip install -r experimenting_ml/requirements.txt

5) Start server:
   cd experimenting_ml
   python run_ui_inference_api.py

6) Open in browser:
   http://127.0.0.1:8000/UI/index.html

Quick validation
----------------
[ ] Scenario Controls visible on left panel
[ ] Run simulation updates KPI cards
[ ] SHAP panel shows explanatory drivers
[ ] Focus KPI dropdown updates SHAP values/model text
[ ] API health returns JSON at /api/health

Troubleshooting
---------------
1) Blank page:
   - Hard refresh (Cmd/Ctrl + Shift + R)
   - Use HTTP URL above (not file://)

2) Package/module errors:
   - Re-activate venv
   - Re-run: pip install -r experimenting_ml/requirements.txt

3) Port conflict:
   python run_ui_inference_api.py --port 8010
   then open http://127.0.0.1:8010/UI/index.html

Zip command
-----------
From project root:

zip -r submission_package_mentor.zip submission_package_mentor -x "*/.venv/*" "*/__pycache__/*" "*.DS_Store"

