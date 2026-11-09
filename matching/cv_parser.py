import pdfplumber
from docx import Document
import re
import os

def extraire_texte_pdf(chemin_fichier):
    texte = ""
    with pdfplumber.open(chemin_fichier) as pdf:
        for page in pdf.pages:
            page_texte = page.extract_text()
            if page_texte:
                texte += page_texte + "\n"
    return texte

def extraire_texte_docx(chemin_fichier):
    doc = Document(chemin_fichier)
    texte = "\n".join([para.text for para in doc.paragraphs])
    return texte

def extraire_texte(chemin_fichier):
    extension = os.path.splitext(chemin_fichier)[1].lower()
    if extension == '.pdf':
        return extraire_texte_pdf(chemin_fichier)
    elif extension == '.docx':
        return extraire_texte_docx(chemin_fichier)
    else:
        raise ValueError("Format de fichier non supporté (PDF ou DOCX uniquement)")

def extraire_email(texte):
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', texte)
    return match.group(0) if match else None

def extraire_telephone(texte):
    # Cherche un numéro marocain ou international (format flexible)
    match = re.search(r'(\+?\d{1,3}[\s.-]?)?(\d{2,3}[\s.-]?){3,5}', texte)
    return match.group(0).strip() if match else None

def analyser_cv(chemin_fichier):
    texte = extraire_texte(chemin_fichier)
    email = extraire_email(texte)
    telephone = extraire_telephone(texte)
    return {
        'texte': texte,
        'email': email,
        'telephone': telephone
    }