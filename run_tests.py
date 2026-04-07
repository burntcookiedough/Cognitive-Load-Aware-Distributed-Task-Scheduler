import asyncio
import httpx
import uuid
import random

async def simulate_user(user_id, client):
    # Transition LOW -> MEDIUM -> HIGH
    for i in range(1, 21):
        # We need the CLS engine to see a rising CLS
        # So we increment keystrokes and context switches slowly
        
        await client.post("http://localhost:8001/telemetry", json={
            "user_id": user_id,
            "keystrokes": i * 6,
            "avg_inter_key_interval": max(10, 100 - i * 4),
            "typing_variance": i * 200,
            "idle_duration": 0.0,
            "tab_switches": int(i / 2),
            "focus_changes": int(i / 3),
            "context_switches": int(i / 2)
        })
        
        # We need current CLS to be MEDIUM (e.g. at i=10) and start predicting HIGH
        
        mode = "CLADS"
        task = {
            "task_id": str(uuid.uuid4()),
            "user_id": user_id,
            "task_type": "build",
            "disruption_class": "HIGH",
            "disruption_score": 0.95
        }
        await client.post("http://localhost:8003/schedule", json={"task": task, "scheduler_mode": mode})
        
        task_baseline = {
            "task_id": str(uuid.uuid4()),
            "user_id": user_id,
            "task_type": "build",
            "disruption_class": "HIGH",
            "disruption_score": 0.95
        }
        await client.post("http://localhost:8003/schedule", json={"task": task_baseline, "scheduler_mode": "BASELINE"})

        await asyncio.sleep(1.0)

async def main():
    async with httpx.AsyncClient() as client:
        tasks = [simulate_user(f"predictive_user_{i}", client) for i in range(5)]
        await asyncio.gather(*tasks)

        await asyncio.sleep(35) # Wait for accuracy coroutines
        r1 = await client.get("http://localhost:8003/benchmarks/summary")
        r2 = await client.get("http://localhost:8003/preemptive-migrations")
        
        import json
        with open("benchmark_results.json", "w") as f:
            json.dump({"summary": r1.json(), "migrations": r2.json()}, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
