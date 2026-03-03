import json
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from app.db.session import SessionLocal
from app.db.models import Lead

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
