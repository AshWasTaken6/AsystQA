from core.pipeline import run_pipeline

result = run_pipeline('x=1', 'python', 'testuser', 'sess123')
print('Pipeline keys:', sorted(result.keys()))
print('Has scan_id:', 'scan_id' in result)
print('Has correlation_id:', 'correlation_id' in result)
print('Has agent_timings:', 'agent_timings' in result)
print('Has confidence:', 'confidence' in result)
print('Has insights:', 'insights' in result)
