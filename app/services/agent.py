import json
from app.services.lead_service import get_or_create_lead, update_profile, set_stage
from app.services.catalog import match_properties

def _parse_money(text: str) -> float | None:
    # parse simples: pega números e interpreta "3000", "3.000", "3k"
    t = text.lower().replace("r$", "").replace(".", "").replace(",", ".").strip()
    if "k" in t:
        try:
            return float(t.replace("k", "")) * 1000
        except Exception:
            return None
    nums = "".join(ch for ch in t if (ch.isdigit() or ch == "."))
    try:
        return float(nums) if nums else None
    except Exception:
        return None

def _contains_yes(text: str) -> bool | None:
    t = text.lower()
    if any(x in t for x in ["sim", "tenho", "possuo", "yes", "s"]):
        return True
    if any(x in t for x in ["não", "nao", "negativo", "n"]):
        return False
    return None

async def handle_message(contact_id: str, text: str) -> dict:
    lead = await get_or_create_lead(contact_id)
    profile = json.loads(lead.profile_json or "{}")

    t = text.strip().lower()

    # Capturas rápidas por palavras-chave (MVP)
    patch = {}

    if profile.get("renda") is None and any(x in t for x in ["renda", "salário", "salario", "ganho", "recebo"]) or t.isdigit():
        val = _parse_money(text)
        if val:
            patch["renda"] = val

    if profile.get("entrada") is None and any(x in t for x in ["entrada", "dou", "tenho", "guardei", "juntei"]):
        val = _parse_money(text)
        if val:
            patch["entrada"] = val

    if profile.get("fgts") is None and "fgts" in t:
        patch["fgts"] = _contains_yes(text)

    if profile.get("mcmv") is None and any(x in t for x in ["mcmv", "minha casa", "casa verde", "subsídio", "subsidio"]):
        patch["mcmv"] = True

    if profile.get("tipo") is None and any(x in t for x in ["apartamento", "apto"]):
        patch["tipo"] = "Apartamento"
    if profile.get("tipo") is None and "casa" in t:
        patch["tipo"] = "Casa"

    # bairros (bem básico, depois vira lista/IA)
    if profile.get("bairro") is None:
        for b in ["campo grande", "jacarepaguá", "jacarepagua", "recreio"]:
            if b in t:
                patch["bairro"] = "Jacarepaguá" if "jacare" in b else b.title()

    if patch:
        lead = await update_profile(lead, patch)
        profile = json.loads(lead.profile_json or "{}")

    # Máquina de estados simples (consultor por etapas)
    await set_stage(lead, "qualificando")

    if profile.get("bairro") is None:
        return {"reply": "Perfeito. Pra eu te indicar só o que faz sentido, qual bairro ou região você quer (e se aceita regiões próximas)?"}

    if profile.get("tipo") is None:
        return {"reply": "Show. Você prefere **apartamento** ou **casa**?"}

    if profile.get("renda") is None:
        return {"reply": "Boa. Qual sua **renda mensal aproximada** (pode ser uma faixa, tipo 3.5k, 5k)?"}

    if profile.get("entrada") is None:
        return {"reply": "E de **entrada**, quanto você consegue colocar agora (mesmo que estimado)?"}

    if profile.get("fgts") is None:
        return {"reply": "Você tem **FGTS** pra usar na compra? (sim/não)"}

    if profile.get("restricao_nome") is None:
        return {"reply": "Última pra eu fechar o cenário: hoje você tem alguma **restrição no nome** (SPC/Serasa)? (sim/não)"}

    # Se chegou aqui, o lead já está “quase pronto” no MVP
    await set_stage(lead, "ofertando")

    props = match_properties(
        bairro=profile.get("bairro"),
        renda=profile.get("renda"),
        entrada=profile.get("entrada"),
        fgts=profile.get("fgts"),
        mcmv=profile.get("mcmv"),
        tipo=profile.get("tipo"),
        limit=3,
    )

    if not props:
        return {"reply": "Com o seu perfil, eu não encontrei uma opção perfeita no catálogo de teste ainda. Quer que eu amplie para bairros próximos ou ajuste o tipo (casa/apto)?"}

    lines = []
    for p in props:
        lines.append(f"• **{p['nome']}** ({p['bairro']}) | {p['tipo']} | R$ {int(float(p['preco'])):,}".replace(",", "."))

    return {
        "reply": (
            "Fechou. Pelo que você me passou, essas opções tendem a encaixar bem:\n\n"
            + "\n".join(lines)
            + "\n\nSe você me confirmar **qual dessas te chamou mais atenção (1, 2 ou 3)**, eu já preparo o próximo passo pra visita/simulação com o corretor."
        )
    }
