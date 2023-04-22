translations = {
    'helptext': {
        'en': "Hi, I'm here to help you manage your bots and create complex rooms settings for you.",
        'de': "Hallo, ich bin hier, um deine Bots zu verwalten und komplexe Raum-Einstellungen für dich zu erstellen.",
    },
    'generic_error': {
        'en': "Sorry, I tried, but I encountered an error. Please check the logs.",
        'de': "Entschuldigung, ich hab's versucht, aber es ist etwas schief gelaufen. Bitte überprüfe die Logs.",
    },
}


def echo(phrase, lang):
    if phrase not in translations:
        return "Phrase not found: " + phrase
    if lang not in translations[phrase]:
        return translations[phrase]['en']
    return translations[phrase][lang]
