import json

from app.services.catalog import match_properties
from app.services.lead_service import get_or_create_lead, set_stage, update_profile


def _parse_money(text: str) -> float | None:
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
    if any(x in t for x in ["sim", "tenho", "possuo", "yes"]):
        return True
    if any(x in t for x in ["nao", "não", "negativo"]):
        return False
    return None


async def handle_message(contact_id: str, text: str) -> dict:
    lead = await get_or_create_lead(contact_id)
    profile = json.loads(lead.profile_json or "{}")

    t = text.strip().lower()
    patch = {}

    if profile.get("renda") is None and (
        any(x in t for x in ["renda", "salario", "salário", "ganho", "recebo"]) or t.isdigit()
    ):
        val = _parse_money(text)
        if val:
            patch["renda"] = val

    if profile.get("entrada") is None and any(x in t for x in ["entrada", "dou", "tenho", "guardei", "juntei"]):
        val = _parse_money(text)
        if val:
            patch["entrada"] = val

    if profile.get("fgts") is None and "fgts" in t:
        patch["fgts"] = _contains_yes(text)

    if profile.get("mcmv") is None and any(x in t for x in ["mcmv", "minha casa", "casa verde", "subsidio", "subsídio"]):
        patch["mcmv"] = True

    if profile.get("tipo") is None and any(x in t for x in ["apartamento", "apto"]):
        patch["tipo"] = "Apartamento"
    if profile.get("tipo") is None and "casa" in t:
        patch["tipo"] = "Casa"

    if profile.get("bairro") is None:
        for b in ["campo grande", "jacarepagua", "jacarepaguá", "recreio"]:
            if b in t:
                patch["bairro"] = "Jacarepaguá" if "jacare" in b else b.title()

    if patch:
        lead = await update_profile(lead, patch)
        profile = json.loads(lead.profile_json or "{}")

    await set_stage(lead, "qualificando")

    if profile.get("bairro") is None:
        return {
            "reply": "Perfeito. Pra eu te indicar so o que faz sentido, qual bairro ou regiao voce quer (e se aceita regioes proximas)?"
        }

    if profile.get("tipo") is None:
        return {"reply": "Show. Voce prefere apartamento ou casa?"}

    if profile.get("renda") is None:
        return {"reply": "Boa. Qual sua renda mensal aproximada (pode ser uma faixa, tipo 3.5k, 5k)?"}

    if profile.get("entrada") is None:
        return {"reply": "E de entrada, quanto voce consegue colocar agora (mesmo que estimado)?"}

    if profile.get("fgts") is None:
        return {"reply": "Voce tem FGTS pra usar na compra? (sim/nao)"}

    if profile.get("restricao_nome") is None:
        return {"reply": "Ultima pra eu fechar o cenario: hoje voce tem alguma restricao no nome (SPC/Serasa)? (sim/nao)"}

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
        return {
            "reply": "Com o seu perfil, eu nao encontrei uma opcao perfeita no catalogo de teste ainda. Quer que eu amplie para bairros proximos ou ajuste o tipo (casa/apto)?"
        }

    lines = []
    for p in props:
        linha = f"- {p['nome']} ({p['bairro']}) | {p['tipo']} | R$ {int(float(p['preco'])):,}".replace(",", ".")
        lines.append(linha)

    return {
        "reply": (
            "Fechou. Pelo que voce me passou, essas opcoes tendem a encaixar bem:\n\n"
            + "\n".join(lines)
            + "\n\nSe voce me confirmar qual dessas te chamou mais atencao (1, 2 ou 3), eu ja preparo o proximo passo pra visita/simulacao com o corretor."
        )
    }
