

from llm_service import demander_au_llm

try:
    reponse = demander_au_llm(
        "Réponds en une phrase : comment améliorer mon CV pour un stage en IA ?",
        provider="Gemini",
        )
    print("\nRéponse de Gemini :")
    print(reponse)

except Exception as erreur:
    print("\nErreur pendant le test :")
    print(type(erreur).__name__, erreur)


