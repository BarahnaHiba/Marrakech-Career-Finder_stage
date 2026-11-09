{% extends "base.html" %}
{% block title %}Assistant IA — Marrakech Career Finder{% endblock %}

{% block content %}
  <div class="chat-header">
    <div>
      <h1 class="page-title">Assistant IA 🤖</h1>
      <p class="stat-label">Pose tes questions sur les CV, les stages, les entretiens et tes études.</p>
    </div>

    <form method="POST">
      <button class="btn btn-small btn-outline" type="submit" name="action" value="nouvelle">
        ➕ Nouvelle conversation
      </button>
    </form>
  </div>

  <section class="chat card" id="chat">
    {% if historique %}
      {% for message in historique %}
        <div class="message {{ 'user' if message.role == 'user' else 'assistant' }}">
          <div class="bubble">
            <span class="sender">{{ 'Toi' if message.role == 'user' else 'Gemini' }}</span>
            {% if message.fichier_nom %}
              <span class="file-chip">📎 {{ message.fichier_nom }}</span>
            {% endif %}
            <div class="texte">{{ message.content }}</div>
            {% if message.role != 'user' %}
              <button type="button" class="speak">🔊 Écouter</button>
            {% endif %}
          </div>
        </div>
      {% endfor %}
    {% else %}
      <div class="welcome">
        <span class="welcome-icon">🤖</span>
        <h2>Bonjour !</h2>
        <p>Je suis ton assistant IA Career Finder.</p>
        <p>Comment puis-je t'aider aujourd'hui ?</p>
      </div>
    {% endif %}
  </section>

  <form method="POST" class="chat-form card" id="form-question" enctype="multipart/form-data">
    <textarea
      id="question"
      name="question"
      placeholder="Écris ton message ici, ou clique sur Parler..."></textarea>

    <div class="chat-actions">
      <label class="btn btn-small btn-outline" for="fichier">📎 Joindre un fichier</label>
      <input type="file" id="fichier" name="fichier" hidden
             accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp">
      <span class="file-name" id="nom-fichier"></span>
      <button type="button" class="file-clear" id="retirer-fichier" title="Retirer le fichier">✕</button>

      <button type="button" class="btn btn-small btn-outline mic" id="bouton-micro">🎤 Parler</button>
      <select id="langue-micro" class="lang" title="Langue de la dictée">
        <option value="fr-FR">Français</option>
        <option value="ar-MA">العربية (المغرب)</option>
        <option value="en-US">English</option>
      </select>

      <button type="submit" name="action" value="envoyer" class="btn send" id="bouton-envoyer">
        Envoyer à Gemini
      </button>
    </div>

    <p class="micro-etat" id="etat-micro" aria-live="polite"></p>

    <div id="zone-lecture-auto">
      <label class="auto-lecture">
        <input type="checkbox" id="lecture-auto">
        🔊 Lire les réponses à voix haute automatiquement
      </label>
    </div>

    <p class="hint">Formats : PDF, DOCX, TXT, PNG, JPG, WEBP — 10 Mo maximum.</p>
  </form>
{% endblock %}

{% block scripts %}
<script>
    const chat = document.getElementById("chat");
    chat.scrollTop = chat.scrollHeight;

    const form = document.getElementById("form-question");
    const champTexte = document.getElementById("question");
    const champFichier = document.getElementById("fichier");
    const nomFichier = document.getElementById("nom-fichier");
    const boutonRetirer = document.getElementById("retirer-fichier");
    const boutonEnvoyer = document.getElementById("bouton-envoyer");
    const etatMicro = document.getElementById("etat-micro");

    function afficherEtat(message, erreur) {
        etatMicro.textContent = message;
        etatMicro.classList.toggle("erreur", !!erreur);
    }

    // Afficher le nom du fichier choisi
    champFichier.addEventListener("change", () => {
        const f = champFichier.files[0];
        nomFichier.textContent = f ? f.name : "";
        boutonRetirer.style.display = f ? "inline" : "none";
    });

    // Retirer le fichier choisi
    boutonRetirer.addEventListener("click", () => {
        champFichier.value = "";
        nomFichier.textContent = "";
        boutonRetirer.style.display = "none";
    });

    // ----- Lecture à voix haute : fonctions de texte -----
    const MOTS_EN = new Set(["the", "and", "to", "of", "is", "you", "for", "with", "that", "this", "your", "are"]);
    const MOTS_FR = new Set(["le", "la", "les", "des", "et", "de", "un", "une", "pour", "avec", "est", "vous", "tu", "que", "dans", "du"]);

    // Enlève les symboles (*, #, liens, emojis...) qui seraient lus à voix haute
    function nettoyerTexte(brut) {
        return brut
            .replace(/```[\s\S]*?```/g, " ")
            .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
            .replace(/https?:\/\/\S+/g, " ")
            .replace(/\p{Extended_Pictographic}/gu, " ")
            .replace(/[*_#`>~|]/g, " ")
            .split("\n")
            .map(l => l.replace(/^\s*[-•]\s+/, "").replace(/[ \t]+/g, " ").trim())
            .filter(l => l.length > 0)
            .map(l => /[.!?:;…؟]$/.test(l) ? l : l + ".")
            .join(" ");
    }

    // Devine la langue du texte : arabe, anglais ou français
    function detecterLangue(texte) {
        const lettres = texte.match(/\p{L}/gu) || [];
        const arabes = texte.match(/[\u0600-\u06FF]/g) || [];
        if (lettres.length && arabes.length / lettres.length > 0.3) return "ar";
        const mots = texte.toLowerCase().match(/[a-zà-ÿ']+/g) || [];
        const en = mots.filter(m => MOTS_EN.has(m)).length;
        const fr = mots.filter(m => MOTS_FR.has(m)).length;
        return en > fr ? "en" : "fr";
    }

    // Coupe en petits morceaux : les longs textes sont coupés par certains navigateurs
    function decouper(texte) {
        const phrases = texte.match(/[^.!?؟…,،;:]+[.!?؟…,،;:]*/g) || [texte];
        const morceaux = [];
        let courant = "";
        for (const p of phrases) {
            if (courant && (courant + p).length > 180) {
                morceaux.push(courant.trim());
                courant = "";
            }
            courant += p;
        }
        if (courant.trim()) morceaux.push(courant.trim());
        return morceaux;
    }

    // ----- Lecture à voix haute -----
    const synth = window.speechSynthesis;
    const caseAuto = document.getElementById("lecture-auto");
    const CODES_LANGUE = { fr: "fr-FR", en: "en-US", ar: "ar-SA" };
    let boutonEnLecture = null;

    function majBoutonLecture(actif) {
        document.querySelectorAll(".speak").forEach(b => {
            const on = b === actif;
            b.classList.toggle("active", on);
            b.textContent = on ? "⏹ Arrêter" : "🔊 Écouter";
        });
        boutonEnLecture = actif;
    }

    function arreterLecture() {
        if (!synth) return;
        synth.cancel();
        majBoutonLecture(null);
    }

    function lire(texteBrut, bouton) {
        if (!synth) return;
        arreterLecture();

        const texte = nettoyerTexte(texteBrut);
        if (!texte) return;

        const langue = detecterLangue(texte);
        const voix = synth.getVoices().find(v => v.lang.toLowerCase().startsWith(langue)) || null;
        if (!voix && langue === "ar") {
            afficherEtat("Aucune voix arabe trouvée sur cet appareil : la lecture peut être incorrecte.", true);
        } else {
            afficherEtat("", false);
        }

        const morceaux = decouper(texte);
        morceaux.forEach((morceau, i) => {
            const u = new SpeechSynthesisUtterance(morceau);
            u.lang = voix ? voix.lang : CODES_LANGUE[langue];
            if (voix) u.voice = voix;
            if (i === morceaux.length - 1) {
                u.onend = () => majBoutonLecture(null);
            }
            u.onerror = (e) => {
                if (e.error === "interrupted" || e.error === "canceled") return;
                if (e.error === "not-allowed") {
                    afficherEtat("Le navigateur bloque la lecture automatique. Clique sur « 🔊 Écouter ».", true);
                } else {
                    afficherEtat("Erreur de lecture : " + e.error, true);
                }
                majBoutonLecture(null);
            };
            synth.speak(u);
        });
        majBoutonLecture(bouton);
    }

    // Les voix se chargent parfois après la page : on les attend un instant
    function quandVoixPretes(suite) {
        if (synth.getVoices().length) return suite();
        let fait = false;
        const go = () => { if (!fait) { fait = true; suite(); } };
        synth.addEventListener("voiceschanged", go, { once: true });
        setTimeout(go, 600);
    }

    if (!synth) {
        document.querySelectorAll(".speak").forEach(b => { b.style.display = "none"; });
        document.getElementById("zone-lecture-auto").style.display = "none";
    } else {
        document.querySelectorAll(".speak").forEach(bouton => {
            bouton.addEventListener("click", () => {
                if (boutonEnLecture === bouton) {
                    arreterLecture();
                } else {
                    lire(bouton.closest(".bubble").querySelector(".texte").textContent, bouton);
                }
            });
        });

        // Lecture automatique (choix gardé par le navigateur)
        try { caseAuto.checked = localStorage.getItem("lecture-auto") === "1"; } catch (e) {}
        caseAuto.addEventListener("change", () => {
            try { localStorage.setItem("lecture-auto", caseAuto.checked ? "1" : "0"); } catch (e) {}
            if (!caseAuto.checked) arreterLecture();
        });

        // Après l'envoi d'un message, lire la nouvelle réponse
        // (changement : on vérifie ".flash" au lieu de ".alert")
        try {
            if (sessionStorage.getItem("lecture-en-attente") === "1") {
                sessionStorage.removeItem("lecture-en-attente");
                const dernier = chat.querySelector(".message:last-child");
                if (caseAuto.checked && !document.querySelector(".flash")
                    && dernier && dernier.classList.contains("assistant")) {
                    quandVoixPretes(() => lire(
                        dernier.querySelector(".texte").textContent,
                        dernier.querySelector(".speak")
                    ));
                }
            }
        } catch (e) {}
    }

    window.addEventListener("pagehide", arreterLecture);

    // ----- Micro : dictée vocale -----
    const boutonMicro = document.getElementById("bouton-micro");
    const choixLangue = document.getElementById("langue-micro");
    const Reconnaissance = window.SpeechRecognition || window.webkitSpeechRecognition;

    let reconnaissance = null;
    let enEcoute = false;
    let erreurMicro = false;
    let texteAvant = "";

    // Retrouver la langue choisie la dernière fois
    try {
        const langueSauvee = localStorage.getItem("langue-micro");
        if (langueSauvee) choixLangue.value = langueSauvee;
    } catch (e) {}

    choixLangue.addEventListener("change", () => {
        try { localStorage.setItem("langue-micro", choixLangue.value); } catch (e) {}
    });

    function majBouton() {
        boutonMicro.classList.toggle("active", enEcoute);
        boutonMicro.textContent = enEcoute ? "⏹ Arrêter" : "🎤 Parler";
    }

    function arreterMicro() {
        if (reconnaissance && enEcoute) reconnaissance.stop();
    }

    function demarrerMicro() {
        arreterLecture();   // l'assistant se tait quand tu veux parler
        erreurMicro = false;
        reconnaissance = new Reconnaissance();
        reconnaissance.lang = choixLangue.value;
        reconnaissance.continuous = true;
        reconnaissance.interimResults = true;

        // On garde ce qui est déjà écrit et on ajoute la voix après
        const dejaEcrit = champTexte.value.trim();
        texteAvant = dejaEcrit ? dejaEcrit + " " : "";

        reconnaissance.onstart = () => {
            enEcoute = true;
            majBouton();
            afficherEtat("🎤 Je t'écoute… parle maintenant.", false);
        };

        reconnaissance.onresult = (event) => {
            let texte = "";
            for (let i = 0; i < event.results.length; i++) {
                texte += event.results[i][0].transcript;
            }
            champTexte.value = texteAvant + texte;
        };

        reconnaissance.onerror = (event) => {
            erreurMicro = true;
            const messages = {
                "not-allowed": "Micro bloqué. Clique sur le cadenas à gauche de l'adresse et autorise le micro.",
                "service-not-allowed": "Micro bloqué. Autorise le micro dans ton navigateur.",
                "no-speech": "Je n'ai rien entendu. Réessaie en parlant plus près du micro.",
                "audio-capture": "Aucun micro détecté sur cet appareil.",
                "network": "La dictée demande une connexion internet.",
                "language-not-supported": "Cette langue n'est pas disponible pour la dictée."
            };
            afficherEtat(messages[event.error] || ("Erreur du micro : " + event.error), true);
        };

        reconnaissance.onend = () => {
            enEcoute = false;
            majBouton();
            if (!erreurMicro) {
                afficherEtat("Dictée terminée. Relis ton texte, puis envoie.", false);
            }
        };

        try {
            reconnaissance.start();
        } catch (e) {
            afficherEtat("Impossible de démarrer le micro. Réessaie.", true);
        }
    }

    if (!Reconnaissance) {
        boutonMicro.disabled = true;
        choixLangue.disabled = true;
        afficherEtat("La dictée vocale n'est pas disponible sur ce navigateur. Utilise Chrome ou Edge.", true);
    } else {
        boutonMicro.addEventListener("click", () => {
            if (enEcoute) {
                arreterMicro();
            } else {
                demarrerMicro();
            }
        });
    }

    // Indiquer que Gemini travaille et éviter le double envoi
    form.addEventListener("submit", () => {
        arreterMicro();
        arreterLecture();
        try {
            if (caseAuto && caseAuto.checked) sessionStorage.setItem("lecture-en-attente", "1");
        } catch (e) {}
        boutonEnvoyer.disabled = true;
        boutonEnvoyer.textContent = "Gemini réfléchit…";
    });
</script>
{% endblock %}