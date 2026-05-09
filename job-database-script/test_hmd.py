import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from backend.app.database import SessionLocal
from backend.app.models.job_source import JobSource
from backend.app.services.job_finder.source_tester import test_job_source

db = SessionLocal()
src = db.query(JobSource).filter(JobSource.company == "hmd_global").first()
print("DB src.company:", repr(src.company))
print(test_job_source({"ats_type": src.ats_type, "base_url": src.base_url, "company": src.company}))
