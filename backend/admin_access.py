import os
from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def email_est_administrateur(email):
    if not email:
        return False
    autorises = {
        valeur.strip().casefold()
        for valeur in os.environ.get("ADMIN_EMAILS", "").split(",")
        if valeur.strip()
    }
    return email.strip().casefold() in autorises


def admin_required(vue):
    @wraps(vue)
    @login_required
    def proteger(*args, **kwargs):
        if not email_est_administrateur(getattr(current_user, "email", None)):
            abort(403)
        return vue(*args, **kwargs)

    return proteger
