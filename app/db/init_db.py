from app.db.session import engine
from app.db.models import Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Corrige historico sem restricao de unicidade em SQLite.
        if conn.dialect.name == "sqlite":
            await conn.exec_driver_sql(
                """
                DELETE FROM leads
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM leads
                    GROUP BY contact_id
                )
                """
            )
            await conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_leads_contact_id ON leads(contact_id)"
            )
