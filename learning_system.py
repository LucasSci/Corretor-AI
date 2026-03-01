"""
Sistema de aprendizado contínuo do bot.
Captura feedback de cada interação e melhora continuamente.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from knowledge_manager import intelligence_core


class ContinuousLearningSystem:
    """Sistema que aprende com cada atendimento."""
    
    def __init__(self):
        self.intelligence_core = intelligence_core
    
    def process_interaction(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa uma interação e extrai aprendizados."""
        
        cliente_numero = interaction_data.get("cliente_numero")
        pergunta = interaction_data.get("pergunta")
        resposta = interaction_data.get("resposta")
        modelo_usado = interaction_data.get("modelo_usado", "gemini")
        
        print(f"\n🧠 [LEARNING] Processando interação do cliente {cliente_numero}")
        
        # 1. Registrar interação
        self.intelligence_core.log_interaction(
            cliente_numero=cliente_numero,
            pergunta=pergunta,
            resposta=resposta
        )
        
        # 2. Processar feedback (se fornecido)
        feedback_data = {
            "cliente": cliente_numero,
            "pergunta": pergunta,
            "modelo": modelo_usado,
            "timestamp": datetime.now().isoformat()
        }
        
        # Se houver rating de satisfação
        if "satisfacao" in interaction_data:
            feedback_data["satisfacao"] = interaction_data["satisfacao"]
            print(f"  ⭐ Satisfação: {interaction_data['satisfacao']}/5")
        
        # Se houver comentário de feedback
        if "feedback_texto" in interaction_data:
            feedback_data["feedback"] = interaction_data["feedback_texto"]
            print(f"  💬 Feedback: {interaction_data['feedback_texto']}")
        
        self.intelligence_core.learning_logger.log_feedback(feedback_data)
        
        # 3. Extrair novos conhecimentos da conversa
        novos_conhecimentos = self._extract_learnings(pergunta, resposta)
        
        for conhecimento in novos_conhecimentos:
            if conhecimento["confianca"] > 0.7:  # Apenas alta confiança
                self.intelligence_core.memory_system.add_corrected_error(
                    erro=conhecimento["tipo"],
                    correcao=conhecimento["valor"]
                )
                print(f"  📝 Novo conhecimento: {conhecimento['tipo']}")
        
        # 4. Atualizar perfil do cliente
        if cliente_numero:
            perfil_existente = self.intelligence_core.memory_system.get_client_profile(cliente_numero)
            
            perfil = perfil_existente or {
                "primeira_interacao": datetime.now().isoformat(),
                "total_interacoes": 0,
                "preferencias": {}
            }
            
            perfil["total_interacoes"] = perfil.get("total_interacoes", 0) + 1
            perfil["ultima_interacao"] = datetime.now().isoformat()
            
            # Extrair preferências
            preferencias = self._extract_preferences(pergunta)
            if preferencias:
                perfil["preferencias"].update(preferencias)
            
            self.intelligence_core.memory_system.add_client_profile(cliente_numero, perfil)
            print(f"  👤 Perfil do cliente atualizado")
        
        return {
            "status": "sucesso",
            "cliente": cliente_numero,
            "conhecimentos_extraidos": len(novos_conhecimentos),
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_learnings(self, pergunta: str, resposta: str) -> List[Dict[str, Any]]:
        """Extrai aprendizados implícitos da conversa."""
        learnings = []
        
        # Palabras-chave que indicam novo conhecimento
        keywords = {
            "preço": 0.9,
            "metragem": 0.9,
            "amenidade": 0.85,
            "localização": 0.85,
            "como": 0.7,
            "qual": 0.7,
            "quando": 0.7,
        }
        
        pergunta_lower = pergunta.lower()
        
        for keyword, confianca in keywords.items():
            if keyword in pergunta_lower:
                learnings.append({
                    "tipo": f"pergunta_{keyword}",
                    "valor": pergunta,
                    "confianca": confianca
                })
        
        return learnings
    
    def _extract_preferences(self, pergunta: str) -> Dict[str, Any]:
        """Extrai preferências do cliente baseado na pergunta."""
        preferencias = {}
        
        pergunta_lower = pergunta.lower()
        
        # Tipo de imóvel
        if "apartamento" in pergunta_lower or "apto" in pergunta_lower:
            preferencias["tipo_imovel"] = "apartamento"
        elif "casa" in pergunta_lower or "sobrado" in pergunta_lower:
            preferencias["tipo_imovel"] = "casa"
        elif "comercial" in pergunta_lower or "sala" in pergunta_lower:
            preferencias["tipo_imovel"] = "comercial"
        
        # Tamanho
        if "grande" in pergunta_lower or "espaçoso" in pergunta_lower:
            preferencias["tamanho"] = "grande"
        elif "pequeno" in pergunta_lower or "compacto" in pergunta_lower:
            preferencias["tamanho"] = "pequeno"
        
        # Budget
        if "barato" in pergunta_lower or "acessível" in pergunta_lower:
            preferencias["budget"] = "baixo"
        elif "luxo" in pergunta_lower or "premium" in pergunta_lower:
            preferencias["budget"] = "alto"
        
        # Localização
        if "barra" in pergunta_lower:
            preferencias["localizacao_preferida"] = "Barra da Tijuca"
        elif "centro" in pergunta_lower:
            preferencias["localizacao_preferida"] = "Centro"
        elif "ipanema" in pergunta_lower or "copacabana" in pergunta_lower:
            preferencias["localizacao_preferida"] = "Zona Sul"
        
        return preferencias
    
    def ingest_successful_response(self, pergunta: str, resposta: str, categoria: str = "resposta_bem_sucedida"):
        """Ingere uma resposta bem-sucedida para melhoria contínua."""
        self.intelligence_core.add_training_data(
            documents=[f"Q: {pergunta}\nA: {resposta}"],
            source="Atendimento real",
            category=categoria
        )
        print(f"✅ Resposta bem-sucedida adicionada ao conhecimento")
    
    def correct_wrong_response(self, pergunta: str, resposta_incorreta: str, 
                              resposta_correta: str):
        """Registra correção de resposta incorreta."""
        self.intelligence_core.memory_system.add_corrected_error(
            erro=resposta_incorreta,
            correcao=resposta_correta
        )
        
        # Adicionar resposta correta ao conhecimento
        self.intelligence_core.add_training_data(
            documents=[f"Q: {pergunta}\nA: {resposta_correta}"],
            source="Correção manual",
            category="resposta_corrigida"
        )
        
        print(f"🔧 Resposta corrigida e adicionada ao conhecimento")
    
    def get_improvement_suggestions(self) -> Dict[str, Any]:
        """Gera sugestões de melhoria baseado em feedback."""
        recent_interactions = self.intelligence_core.learning_logger.get_recent_learnings(50)
        
        low_satisfaction = []
        frequent_questions = {}
        models_performance = {"gemini": {"total": 0, "satisfied": 0}, 
                             "openai": {"total": 0, "satisfied": 0}}
        
        for interaction in recent_interactions:
            if interaction.get("tipo") == "feedback":
                satisfacao = interaction.get("satisfacao", 3)
                if satisfacao and satisfacao < 3:
                    low_satisfaction.append(interaction)
                
                modelo = interaction.get("modelo", "unknown")
                if modelo in models_performance:
                    models_performance[modelo]["total"] += 1
                    if satisfacao and satisfacao >= 4:
                        models_performance[modelo]["satisfied"] += 1
            
            elif interaction.get("tipo") == "interacao":
                pergunta = interaction.get("pergunta", "")
                if pergunta:
                    frequent_questions[pergunta] = frequent_questions.get(pergunta, 0) + 1
        
        top_questions = sorted(frequent_questions.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "low_satisfaction_count": len(low_satisfaction),
            "top_questions": [q[0] for q in top_questions],
            "models_performance": models_performance,
            "suggestions": self._generate_suggestions(low_satisfaction, top_questions)
        }
    
    def _generate_suggestions(self, low_satisfaction: List, top_questions: List) -> List[str]:
        """Gera sugestões de melhoria."""
        suggestions = []
        
        if len(low_satisfaction) > 5:
            suggestions.append(
                "⚠️ Muitos clientes com baixa satisfação. Revisar respostas frequentes."
            )
        
        if top_questions:
            suggestions.append(
                f"💡 Perguntas frequentes: {', '.join([q[0][:30] for q in top_questions[:3]])}. "
                "Considere adicionar respostas pré-prontas."
            )
        
        suggestions.append(
            "📚 Adicione mais documentação sobre produtos para melhorar respostas."
        )
        
        return suggestions


# Instância global
learning_system = ContinuousLearningSystem()


if __name__ == "__main__":
    print("🎓 Sistema de Aprendizado Contínuo Inicializado\n")
    
    # Teste
    exemplo_interacao = {
        "cliente_numero": "5521987654321",
        "pergunta": "Qual apartamento vocês têm com melhor preço e piscina?",
        "resposta": "Recomendo o Duet Barra com 2 quartos por R$ 800 mil, que possui piscina e playground",
        "satisfacao": 5,
        "feedback_texto": "Resposta perfeita!",
        "modelo_usado": "gemini"
    }
    
    resultado = learning_system.process_interaction(exemplo_interacao)
    print(f"\n✅ Resultado: {json.dumps(resultado, indent=2, ensure_ascii=False)}")
    
    # Mostrar sugestões
    print("\n📊 Sugestões de Melhoria:")
    suggestions = learning_system.get_improvement_suggestions()
    for suggestion in suggestions.get("suggestions", []):
        print(f"  {suggestion}")
