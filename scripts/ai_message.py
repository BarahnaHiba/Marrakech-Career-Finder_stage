import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM = (
    "Tu rédiges des emails de candidature spontanée pour un stage, en français, "
    "à la première personne, ton professionnel et naturel. "
    "Maximum 150 mots. Pas de formule générique creuse. "
    "N'invente aucune expérience : utilise uniquement les informations du CV fourni. "
    "Termine par la formule de politesse et la signature."
)

def generer_message_ia(nom, email, cv_texte, entreprise, secteur, poste):
    prompt = f"""Rédige un email de candidature spontanée.

Candidate : {nom} ({email})
Poste visé : {poste}
Entreprise : {entreprise} (secteur : {secteur})

CV de la candidate :
{cv_texte[:3000]}

Format : une ligne « Objet : ... », puis le corps du message.
Mentionne que le CV est joint. Relie 1 ou 2 éléments précis du CV
(projet, certificat, stage) à l'activité de l'entreprise."""
    resp = client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=600,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()