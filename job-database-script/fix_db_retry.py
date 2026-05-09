import sys, os, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from backend.app.database import SessionLocal
from backend.app.models.job_source import JobSource
from backend.app.services.job_finder.source_tester import test_job_source

db = SessionLocal()
sources = db.query(JobSource).filter(JobSource.ats_type == "ashby", JobSource.enabled == True).all()

invalidated = 0
for src in sources:
    while True:
        res = test_job_source({"ats_type": src.ats_type, "base_url": src.base_url, "company": src.company})
        if res["status"] == "blocked":
            print(f"Rate limited on {src.company}, sleeping 2s...")
            time.sleep(2)
            continue
        elif res["status"] == "invalid":
            print(f"Fixing false positive: {src.company}")
            src.enabled = False
            src.status = "invalid"
            src.last_error = res.get("error")
            invalidated += 1
            db.commit()
            break
        else:
            break
    time.sleep(0.1)

print(f"Total fixed: {invalidated}")
