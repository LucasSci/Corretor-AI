"""
Script de exemplo para carregar dados de treinamento.
Demonstra como alimentar a base de inteligência com conhecimento.
"""

import json
from data_ingestion import ingestion_pipeline
from knowledge_manager import intelligence_core
from learning_system import learning_system


def exemplo_1_imoveis():
    """Exemplo 1: Adicionar dados de imóveis."""
    print("\n" + "="*60)
    print("EXEMPLO 1: Adicionando dados de imóveis")
    print("="*60)
    
    imoveis = [
        {
            "nome": "Apogeu Barra",
            "localizacao": "Barra da Tijuca, Rio de Janeiro",
            "descricao": "Empreendimento de luxo com acabamento premium e tecnologia inteligente",
            "amenidades": [
                "2 Piscinas (uma aquecida)",
                "Spa completo",
                "Academia com personal",
                "Playground infantil",
                "Salão de festas",
                "Churrasqueira",
                "Coworking",
                "Garagens com 2 vagas"
            ],
            "precos": {
                "Studio": "450000",
                "1 Quarto": "650000",
                "2 Quartos": "950000",
                "3 Quartos": "1350000"
            }
        },
        {
            "nome": "Duet Barra",
            "localizacao": "Barra da Tijuca, Rio de Janeiro",
            "descricao": "Apartamentos modernos com varanda gourmet e vista para o mar",
            "amenidades": [
                "Piscina com borda infinita",
                "Quadra de esportes",
                "Coworking",
                "Playground",
                "Salão de jogos"
            ],
            "precos": {
                "2 Quartos": "800000",
                "3 Quartos": "1200000"
            }
        },
        {
            "nome": "Ilhamar Beach Home",
            "localizacao": "Barra da Tijuca",
            "descricao": "Residencial com foco em lazer e segurança para famílias",
            "amenidades": [
                "Piscina",
                "Playground completo",
                "Quadra de tênis",
                "Espaço gourmet"
            ],
            "precos": {
                "2 Quartos": "650000",
                "3 Quartos": "950000",
                "Cobertura": "1500000"
            }
        }
    ]
    
    ingestion_pipeline.ingest_properties_batch(imoveis)


def exemplo_2_conhecimento_direto():
    """Exemplo 2: Adicionar conhecimento direto."""
    print("\n" + "="*60)
    print("EXEMPLO 2: Adicionando conhecimento direto")
    print("="*60)
    
    conhecimentos = [
        """
        Barra da Tijuca é uma região em expansão no Rio de Janeiro, ideal para clientes 
        que buscam modernidade, segurança e qualidade de vida. É conhecida por praias limpas, 
        shopping centers, restaurantes e parques temáticos. A região oferece ótima 
        valorização de imóveis a longo prazo.
        """,
        """
        Apartamentos de luxo em Barra oferecem:
        - Vista para o mar ou lagoas
        - Acabamento premium
        - Tecnologia de automação residencial
        - Segurança 24 horas
        - Estacionamento seguro
        - Proximidade com comércio e serviços
        """,
        """
        Para financiamento de imóveis:
        - Caixa Econômica Federal (até 85% do valor)
        - Banco do Brasil (até 80% do valor)
        - Santander (programas especiais)
        - Bradesco (taxa competitiva)
        - Itaú (Habitacional)
        """,
        """
        Dicas de venda premium:
        1. Destaque a localização e proximidade com comércio
        2. Realce as amenidades e qualidade de vida
        3. Mencione a valorização histórica da região
        4. Ressalte a segurança e o design moderno
        5. Ofereça flexibilidade nas condições de pagamento
        6. Realize visitas virtuais em 360 graus
        7. Destaque diferenciais como varanda, home office, etc
        """
    ]
    
    for i, conhecimento in enumerate(conhecimentos, 1):
        ingestion_pipeline.add_custom_knowledge(
            knowledge_text=conhecimento,
            categoria=f"propriedade_barra_{i}"
        )


def exemplo_3_arquivos_texto():
    """Exemplo 3: Importar arquivos de texto."""
    print("\n" + "="*60)
    print("EXEMPLO 3: Importando arquivos de texto (se existirem)")
    print("="*60)
    
    import os
    
    # Procurar por PDFs
    if os.path.exists("./documentos"):
        print("📁 Encontrada pasta 'documentos', processando...")
        ingestion_pipeline.ingest_pdf_folder("./documentos", categoria="documento")
    else:
        print("ℹ️  Pasta 'documentos' não encontrada (não é obrigatório)")
    
    # Procurar por TXTs
    if os.path.exists("./dados"):
        print("📁 Encontrada pasta 'dados', processando...")
        ingestion_pipeline.ingest_text_folder("./dados", categoria="dados")
    else:
        print("ℹ️  Pasta 'dados' não encontrada (não é obrigatório)")


def exemplo_4_json_dados():
    """Exemplo 4: Importar dados estruturados JSON."""
    print("\n" + "="*60)
    print("EXEMPLO 4: Importando dados estruturados")
    print("="*60)
    
    # Criar arquivo JSON de exemplo
    exemplo_data = {
        "imoveis_premium": [
            {
                "id": 1,
                "nome": "Marina Residence",
                "valor": 2500000,
                "area": 250,
                "quartos": 3,
                "suites": 2
            }
        ],
        "perguntas_frequentes": [
            {
                "pergunta": "Qual é o valor do IPTU?",
                "resposta": "O IPTU varia conforme a localização e tamanho. Pode representar 0.5% a 1.2% do valor do imóvel anualmente."
            },
            {
                "pergunta": "É possível fazer reforma?",
                "resposta": "Sim, desde que com aprovação prévia da administração e sem alterar a estrutura."
            }
        ]
    }
    
    with open("./exemplo_dados.json", "w", encoding="utf-8") as f:
        json.dump(exemplo_data, f, ensure_ascii=False, indent=2)
    
    ingestion_pipeline.ingest_json_file("./exemplo_dados.json", categoria="dados_estruturados")


def exemplo_5_simular_interacoes():
    """Exemplo 5: Simular interações para testes."""
    print("\n" + "="*60)
    print("EXEMPLO 5: Simulando interações de clientes")
    print("="*60)
    
    interacoes_teste = [
        {
            "cliente_numero": "5521912345678",
            "pergunta": "Qual é o melhor apartamento com piscina?",
            "resposta": "Recomendo o Duet Barra com 2 quartos (R$ 800 mil), que tem piscina com borda infinita e vista mar!",
            "satisfacao": 5,
            "feedback_texto": "Excelente recomendação!"
        },
        {
            "cliente_numero": "5521987654321",
            "pergunta": "Quais imóveis são mais acessíveis?",
            "resposta": "O Ilhamar Beach Home tem ótimas opções a partir de R$ 650 mil para 2 quartos!",
            "satisfacao": 4,
            "feedback_texto": "Bom!"
        }
    ]
    
    for interacao in interacoes_teste:
        resultado = learning_system.process_interaction(interacao)
        print(f"  ✅ Interação processada: {resultado}")


def exemplo_6_consultar_estatisticas():
    """Exemplo 6: Consultar estatísticas."""
    print("\n" + "="*60)
    print("EXEMPLO 6: Estatísticas do sistema")
    print("="*60)
    
    stats = intelligence_core.get_bot_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))


def exemplo_7_buscar_conhecimento():
    """Exemplo 7: Testar busca de conhecimento."""
    print("\n" + "="*60)
    print("EXEMPLO 7: Testando busca de conhecimento")
    print("="*60)
    
    queries = [
        "Quais imóveis com piscina vocês têm?",
        "Qual é o preço dos apartamentos?",
        "Duet Barra tem playground?"
    ]
    
    for query in queries:
        print(f"\n🔍 Buscando: '{query}'")
        resultados = intelligence_core.search_knowledge(query, n_results=3)
        for i, (doc, confianca) in enumerate(zip(resultados['documents'], resultados['similarities']), 1):
            print(f"  {i}. (Confiança: {confianca:.2f})")
            print(f"     {doc[:100]}...")


def main():
    """Executa exemplo completo de treinamento."""
    print("\n" + "#"*60)
    print("# 🧠 SISTEMA DE TREINAMENTO - EXEMPLO COMPLETO")
    print("#"*60)
    
    # Executar exemplos
    exemplo_1_imoveis()
    exemplo_2_conhecimento_direto()
    exemplo_3_arquivos_texto()
    exemplo_4_json_dados()
    exemplo_5_simular_interacoes()
    exemplo_6_consultar_estatisticas()
    exemplo_7_buscar_conhecimento()
    
    print("\n" + "#"*60)
    print("# ✅ TREINAMENTO CONCLUÍDO")
    print("#"*60)
    print("""
PRÓXIMOS PASSOS:
1. Coloque PDFs de produtos em ./documentos/
2. Coloque dados em ./dados/
3. Execute este script regularmente para atualizar o conhecimento
4. O bot aprenderá automaticamente com cada interação no WhatsApp
5. Use learning_system.get_improvement_suggestions() para feedback
    """)


if __name__ == "__main__":
    main()
