import asyncio
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.db.models import Base
from app.db.session import engine, SessionLocal
from app.services.lead_service import update_profile, set_stage, get_or_create_lead

async def setup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def teardown():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def run_benchmark(num_iterations=100):
    await setup()

    # Create the lead initially
    contact_id = "test_benchmark_contact"
    await get_or_create_lead(contact_id)

    start_time = time.perf_counter()

    lead = await get_or_create_lead(contact_id)
    for i in range(num_iterations):
        patch = {"renda": i}
        await update_profile(lead, patch)
        await set_stage(lead, f"stage_{i}")

    end_time = time.perf_counter()
    duration = end_time - start_time

    print(f"Benchmark completed: {num_iterations} iterations in {duration:.4f} seconds")
    print(f"Average time per iteration: {(duration / num_iterations) * 1000:.2f} ms")

    await teardown()

if __name__ == "__main__":
    asyncio.run(run_benchmark())
