translations = {
    'helptext': {
        'en': "Hi, I'm here to help you manage your bots and create complex rooms settings for you.",
        'de': "Hallo, ich bin hier, um dir zu helfen, deine Bots zu verwalten und komplexe Raum-Einstellungen für dich zu erstellen.",
    },
    'generic_error': {
        'en': "Sorry, I tried, but I encountered an error. Please check the logs.",
        'de': "Entschuldigung, ich hab's versucht, aber es ist etwas schief gelaufen. Bitte überprüfe die Logs.",
    },
}


def echo(phrase, lang):
    return translations[phrase][lang]
