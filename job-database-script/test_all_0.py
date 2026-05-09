import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from backend.app.database import SessionLocal
from backend.app.models.job_source import JobSource
from backend.app.services.job_finder.source_tester import test_job_source

db = SessionLocal()
sources = db.query(JobSource).filter(JobSource.ats_type == "ashby", JobSource.enabled == True, JobSource.total_jobs_found == 0).all()
for src in sources:
    res = test_job_source({"ats_type": src.ats_type, "base_url": src.base_url, "company": src.company})
    if res["status"] == "invalid":
        print(f"FAILED NOW: {src.company}")
    else:
        print(f"STILL VALID: {src.company}")
