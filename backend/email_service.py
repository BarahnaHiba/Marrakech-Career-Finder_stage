import os
import smtplib
from email.message import EmailMessage


DUREE_CODE_MINUTES = 10


def envoyer_email_code(destinataire, nom, code):
    brevo_login = os.environ.get("BREVO_SMTP_LOGIN")
    brevo_cle = os.environ.get("BREVO_SMTP_KEY")
    brevo_expediteur = os.environ.get("EMAIL_EXPEDITEUR")
    gmail_adresse = os.environ.get("GMAIL_ADDRESS")
    gmail_mot_de_passe = os.environ.get("GMAIL_APP_PASSWORD")

    if brevo_login and brevo_cle and brevo_expediteur:
        fournisseur = "brevo"
        expediteur = brevo_expediteur
    elif gmail_adresse and gmail_mot_de_passe:
        fournisseur = "gmail"
        expediteur = gmail_adresse
        gmail_mot_de_passe = "".join(gmail_mot_de_passe.split())
    else:
        raise RuntimeError(
            "Configure BREVO_SMTP_LOGIN, BREVO_SMTP_KEY et EMAIL_EXPEDITEUR, "
            "ou GMAIL_ADDRESS et GMAIL_APP_PASSWORD."
        )

    message = EmailMessage()
    message["Subject"] = f"Ton code de vérification : {code} — Marrakech Career Finder"
    message["From"] = f"Marrakech Career Finder <{expediteur}>"
    message["To"] = destinataire
    message["Reply-To"] = expediteur
    message.set_content(
        f"Bonjour {nom},\n\n"
        "Voici ton code pour vérifier ton compte Marrakech Career Finder :\n\n"
        f"        {code}\n\n"
        f"Ce code est valable {DUREE_CODE_MINUTES} minutes. "
        "Saisis-le dans l'application pour terminer ta connexion.\n\n"
        "Si tu n'es pas à l'origine de cette demande, ignore simplement ce message.\n\n"
        "Marrakech Career Finder"
    )
    message.add_alternative(
        f"<p>Bonjour {nom},</p>"
        "<p>Voici ton code pour vérifier ton compte Marrakech Career Finder :</p>"
        f"<p style='font-size:28px;font-weight:bold;letter-spacing:6px'>{code}</p>"
        f"<p>Ce code est valable {DUREE_CODE_MINUTES} minutes.</p>"
        "<p>Si tu n'es pas à l'origine de cette demande, ignore ce message.</p>",
        subtype="html",
    )

    if fournisseur == "brevo":
        with smtplib.SMTP("smtp-relay.brevo.com", 587, timeout=20) as serveur:
            serveur.starttls()
            serveur.login(brevo_login, brevo_cle)
            refus = serveur.send_message(message)
    else:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as serveur:
            serveur.login(gmail_adresse, gmail_mot_de_passe)
            refus = serveur.send_message(message)

    if refus:
        raise RuntimeError(f"Adresse refusée par le serveur : {refus}")
