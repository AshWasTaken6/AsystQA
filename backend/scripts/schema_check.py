import sys
import traceback

from core.pipeline import run_pipeline
from schemas.response import AnalyzeResponse

try:
    result = run_pipeline('x=1', 'python', 'testuser', 'sess123')
    validated = AnalyzeResponse(**result)
    print("SCHEMA_OK: scan_id=" + validated.scan_id[:8] + " confidence=" + str(validated.confidence))
except Exception as e:
    print("SCHEMA_FAIL: " + str(e))
    traceback.print_exc()
    sys.exit(1)
