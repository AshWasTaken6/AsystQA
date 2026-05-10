#!/usr/bin/env python
"""
Test sentinel step by step.
"""

import asyncio
import sys
sys.path.insert(0, '.')

async def main():
    print("Import", flush=True)
    from core.agent_factory import create_agent
    print("Create agent", flush=True)
    agent = create_agent('sentinel')
    print("Agent created, state:", agent.state, flush=True)
    print("Calling execute", flush=True)
    code = 'def foo():\n    return 1'
    result = await agent.execute(code, 'python')
    print("Result count:", len(result), flush=True)
    for f in result:
        print(f.issue, f.severity, flush=True)
    print("Done", flush=True)

asyncio.run(main())
