from unittest.mock import patch

import pytest

import email_service


def nettoyer_configuration(monkeypatch):
    for nom in (
        "BREVO_SMTP_LOGIN",
        "BREVO_SMTP_KEY",
        "EMAIL_EXPEDITEUR",
        "GMAIL_ADDRESS",
        "GMAIL_APP_PASSWORD",
    ):
        monkeypatch.delenv(nom, raising=False)


def test_envoie_code_par_brevo(monkeypatch):
    nettoyer_configuration(monkeypatch)
    monkeypatch.setenv("BREVO_SMTP_LOGIN", "login")
    monkeypatch.setenv("BREVO_SMTP_KEY", "cle")
    monkeypatch.setenv("EMAIL_EXPEDITEUR", "expediteur@example.com")

    with patch.object(email_service.smtplib, "SMTP") as smtp:
        serveur = smtp.return_value.__enter__.return_value
        serveur.send_message.return_value = {}

        email_service.envoyer_email_code("destinataire@example.com", "Hiba", "123456")

    smtp.assert_called_once_with("smtp-relay.brevo.com", 587, timeout=20)
    serveur.starttls.assert_called_once_with()
    serveur.login.assert_called_once_with("login", "cle")
    message = serveur.send_message.call_args.args[0]
    assert message["To"] == "destinataire@example.com"
    assert "expediteur@example.com" in message["From"]
    assert "123456" in message.get_body(preferencelist=("plain",)).get_content()


def test_envoie_code_par_gmail_en_nettoyant_le_mot_de_passe(monkeypatch):
    nettoyer_configuration(monkeypatch)
    monkeypatch.setenv("GMAIL_ADDRESS", "expediteur@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "abcd efgh\n")

    with patch.object(email_service.smtplib, "SMTP_SSL") as smtp_ssl:
        serveur = smtp_ssl.return_value.__enter__.return_value
        serveur.send_message.return_value = {}

        email_service.envoyer_email_code("destinataire@example.com", "Hiba", "654321")

    smtp_ssl.assert_called_once_with("smtp.gmail.com", 465, timeout=20)
    serveur.login.assert_called_once_with("expediteur@gmail.com", "abcdefgh")
    message = serveur.send_message.call_args.args[0]
    assert message["To"] == "destinataire@example.com"
    assert "654321" in message.get_body(preferencelist=("plain",)).get_content()


def test_brevo_est_prioritaire_quand_les_deux_configurations_sont_completes(monkeypatch):
    nettoyer_configuration(monkeypatch)
    monkeypatch.setenv("BREVO_SMTP_LOGIN", "login")
    monkeypatch.setenv("BREVO_SMTP_KEY", "cle")
    monkeypatch.setenv("EMAIL_EXPEDITEUR", "brevo@example.com")
    monkeypatch.setenv("GMAIL_ADDRESS", "gmail@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "mot-de-passe")

    with patch.object(email_service.smtplib, "SMTP") as smtp:
        smtp.return_value.__enter__.return_value.send_message.return_value = {}
        email_service.envoyer_email_code("destinataire@example.com", "Hiba", "111111")

    smtp.assert_called_once_with("smtp-relay.brevo.com", 587, timeout=20)


def test_configuration_email_manquante_est_signalee(monkeypatch):
    nettoyer_configuration(monkeypatch)

    with patch.object(email_service.smtplib, "SMTP") as smtp:
        with pytest.raises(RuntimeError, match="Configure"):
            email_service.envoyer_email_code("destinataire@example.com", "Hiba", "123456")

    smtp.assert_not_called()


def test_adresse_refusee_par_le_serveur_est_signalee(monkeypatch):
    nettoyer_configuration(monkeypatch)
    monkeypatch.setenv("GMAIL_ADDRESS", "expediteur@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "mot-de-passe")

    with patch.object(email_service.smtplib, "SMTP_SSL") as smtp_ssl:
        serveur = smtp_ssl.return_value.__enter__.return_value
        serveur.send_message.return_value = {"destinataire@example.com": (550, b"refuse")}

        with pytest.raises(RuntimeError, match="Adresse refusée"):
            email_service.envoyer_email_code("destinataire@example.com", "Hiba", "123456")


def test_email_reinitialisation_utilise_brevo_et_contient_le_lien(monkeypatch):
    nettoyer_configuration(monkeypatch)
    monkeypatch.setenv("BREVO_SMTP_LOGIN", "login")
    monkeypatch.setenv("BREVO_SMTP_KEY", "cle")
    monkeypatch.setenv("EMAIL_EXPEDITEUR", "expediteur@example.com")

    with patch.object(email_service.smtplib, "SMTP") as smtp:
        serveur = smtp.return_value.__enter__.return_value
        serveur.send_message.return_value = {}

        email_service.envoyer_email_reinitialisation(
            "destinataire@example.com", "Hiba", "https://exemple.test/reinitialiser/jeton"
        )

    smtp.assert_called_once_with("smtp-relay.brevo.com", 587, timeout=20)
    serveur.starttls.assert_called_once_with()
    serveur.login.assert_called_once_with("login", "cle")
    message = serveur.send_message.call_args.args[0]
    assert message["To"] == "destinataire@example.com"
    assert "expediteur@example.com" in message["From"]
    assert "https://exemple.test/reinitialiser/jeton" in message.get_content()
    assert "valable 1 heure" in message.get_content()


def test_email_reinitialisation_utilise_gmail_si_brevo_incomplet(monkeypatch):
    nettoyer_configuration(monkeypatch)
    monkeypatch.setenv("BREVO_SMTP_LOGIN", "login-incomplet")
    monkeypatch.setenv("GMAIL_ADDRESS", "expediteur@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "abcd efgh\n")

    with patch.object(email_service.smtplib, "SMTP_SSL") as smtp_ssl:
        serveur = smtp_ssl.return_value.__enter__.return_value
        serveur.send_message.return_value = {}

        email_service.envoyer_email_reinitialisation(
            "destinataire@example.com", "Hiba", "https://exemple.test/reinitialiser/jeton"
        )

    smtp_ssl.assert_called_once_with("smtp.gmail.com", 465, timeout=20)
    serveur.login.assert_called_once_with("expediteur@gmail.com", "abcdefgh")
    message = serveur.send_message.call_args.args[0]
    assert message["From"] == "Marrakech Career Finder <expediteur@gmail.com>"
    assert "https://exemple.test/reinitialiser/jeton" in message.get_content()
