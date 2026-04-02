import asyncio

import httpx

from app.db.init_db import init_db
from app.main import app


def test_chat_concurrency_same_contact_no_500():
    async def _run():
        await init_db()
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            tasks = [
                client.post(
                    "/chat",
                    json={"contact_id": "concurrency-user", "text": f"mensagem {i}"},
                )
                for i in range(5)
            ]
            responses = await asyncio.gather(*tasks)

        statuses = [r.status_code for r in responses]
        assert all(s == 200 for s in statuses), statuses

    asyncio.run(_run())
