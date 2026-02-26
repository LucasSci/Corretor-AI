import json
from sqlalchemy import select, update
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
        res = await session.execute(select(Lead).where(Lead.contact_id == contact_id))
        lead = res.scalar_one_or_none()
        if lead:
            return lead

        lead = Lead(contact_id=contact_id, stage="novo", profile_json=json.dumps(DEFAULT_PROFILE))
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        return lead

def _merge_profile(old: dict, new: dict) -> dict:
    merged = {**old}
    for k, v in new.items():
        if v is not None:
            merged[k] = v
    return merged

async def update_profile(contact_id: str, patch: dict) -> Lead:
    lead = await get_or_create_lead(contact_id)
    old = json.loads(lead.profile_json or "{}")
    merged = _merge_profile(old, patch)

    async with SessionLocal() as session:
        await session.execute(
            update(Lead)
            .where(Lead.contact_id == contact_id)
            .values(profile_json=json.dumps(merged))
        )
        await session.commit()

    lead.profile_json = json.dumps(merged)
    return lead

async def set_stage(contact_id: str, stage: str) -> Lead:
    lead = await get_or_create_lead(contact_id)
    async with SessionLocal() as session:
        await session.execute(
            update(Lead).where(Lead.contact_id == contact_id).values(stage=stage)
        )
        await session.commit()
    lead.stage = stage
    return lead
