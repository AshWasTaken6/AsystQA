from core.pipeline import run_pipeline
from schemas.response import AnalyzeResponse

# Run pipeline
result = run_pipeline('x=1', 'python', 'testuser', 'sess123')

# Validate against schema
try:
    validated = AnalyzeResponse(**result)
    print("✓ Response matches schema")
    print(f"  Fields: scan_id={validated.scan_id[:8]}..., confidence={validated.confidence:.2f}")
except Exception as e:
    print(f"✗ Schema validation failed: {e}")
    print(f"  Result keys: {list(result.keys())}")
