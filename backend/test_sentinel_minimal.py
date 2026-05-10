#!/usr/bin/env python
"""
Minimal test for sentinel agent to isolate hanging issue.
"""

import asyncio
import sys
sys.path.insert(0, '.')

async def main():
    print("=== Test 1: Import ===", flush=True)
    from agents.sentinel import SentinelAgent
    print("SentinelAgent imported", flush=True)

    print("\n=== Test 2: Create agent ===", flush=True)
    agent = SentinelAgent(agent_id="test-sentinel")
    print("Agent created, state:", agent.state, flush=True)

    print("\n=== Test 3: Initialize ===", flush=True)
    agent.initialize()
    print("Initialized, state:", agent.state, flush=True)

    print("\n=== Test 4: Execute simple code ===", flush=True)
    code = "def add(a, b):\n    return a + b"
    result = await asyncio.wait_for(agent.execute(code, "python"), timeout=10.0)
    print("Execute returned:", len(result), "findings", flush=True)
    for f in result[:3]:
        print(" -", f.get("issue"), flush=True)

    print("\nAll tests passed!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
