import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database import SessionLocal
from backend.app.models.job_source import JobSource
from backend.app.services.job_finder.source_tester import test_job_source

def main():
    print("Connecting to database...")
    db = SessionLocal()
    
    # Get all enabled Ashby sources
    ashby_sources = db.query(JobSource).filter(JobSource.ats_type == 'ashby', JobSource.enabled == True).all()
    
    print(f"Found {len(ashby_sources)} active Ashby sources to re-verify.")
    
    invalidated_count = 0
    verified_count = 0
    
    for src in ashby_sources:
        print(f"Re-verifying: {src.base_url}...")
        
        test_dict = {
            "ats_type": src.ats_type,
            "base_url": src.base_url,
            "company": src.company
        }
        
        result = test_job_source(test_dict)
        
        if result["status"] == "invalid":
            print(f"  ❌ Invalidated! ({result.get('error')})")
            src.enabled = False
            src.status = "invalid"
            src.last_error = result.get('error')
            invalidated_count += 1
        else:
            print(f"  ✅ Verified! ({result.get('jobs_found')} jobs)")
            src.status = "valid"
            src.total_jobs_found = result.get('jobs_found', 0)
            verified_count += 1
            
        db.commit()
        
    print(f"\nRe-verification complete!")
    print(f"Total Ashby sources re-verified: {len(ashby_sources)}")
    print(f"Valid: {verified_count}")
    print(f"Invalidated (False Positives): {invalidated_count}")

if __name__ == "__main__":
    main()
