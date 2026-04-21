import json

from sqlalchemy import desc, func, select, update
from sqlalchemy.exc import IntegrityError

from app.db.models import Lead
from app.db.session import SessionLocal

DEFAULT_PROFILE = {
    "nome": None,
    "bairro": None,
    "tipo": None,
    "renda": None,
    "entrada": None,
    "fgts": None,
    "mcmv": None,
    "restricao_nome": None,
    "urgencia": None,
    "imoveis_sugeridos": [],
}

async def get_or_create_lead(contact_id: str) -> Lead:
    async with SessionLocal() as session:
        res = await session.execute(
            select(Lead).where(Lead.contact_id == contact_id).order_by(Lead.id.asc()).limit(1)
        )
        lead = res.scalar_one_or_none()
        if lead:
            return lead

        lead = Lead(contact_id=contact_id, stage="novo", profile_json=json.dumps(DEFAULT_PROFILE))
        session.add(lead)
        try:
            await session.commit()
        except IntegrityError:
            # Corrida de concorrencia: outro request inseriu o mesmo contato.
            await session.rollback()
            res = await session.execute(
                select(Lead).where(Lead.contact_id == contact_id).order_by(Lead.id.asc()).limit(1)
            )
            existing = res.scalar_one_or_none()
            if existing is not None:
                return existing
            raise

        await session.refresh(lead)
        return lead

def _merge_profile(old: dict, new: dict) -> dict:
    merged = {**old}
    for k, v in new.items():
        if v is not None:
            merged[k] = v
    return merged

async def update_profile(lead: Lead, patch: dict) -> Lead:
    old = json.loads(lead.profile_json or "{}")
    merged = _merge_profile(old, patch)

    async with SessionLocal() as session:
        await session.execute(
            update(Lead)
            .where(Lead.id == lead.id)
            .values(profile_json=json.dumps(merged))
        )
        await session.commit()

    lead.profile_json = json.dumps(merged)
    return lead

async def set_stage(lead: Lead, stage: str) -> Lead:
    async with SessionLocal() as session:
        await session.execute(
            update(Lead).where(Lead.id == lead.id).values(stage=stage)
        )
        await session.commit()
    lead.stage = stage
    return lead


async def list_leads(limit: int = 50) -> list[dict]:
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Lead).order_by(desc(Lead.created_at)).limit(max(1, min(limit, 200)))
            )
        ).scalars().all()

    items = []
    for row in rows:
        try:
            profile = json.loads(row.profile_json or "{}")
        except Exception:
            profile = {}

        items.append(
            {
                "id": row.id,
                "contact_id": row.contact_id,
                "stage": row.stage,
                "profile": profile,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return items


async def get_lead_counts() -> dict[str, int]:
    async with SessionLocal() as session:
        total = await session.scalar(select(func.count()).select_from(Lead))
    return {"total": int(total or 0)}
