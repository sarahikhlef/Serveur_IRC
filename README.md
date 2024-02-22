# Réalisé par: 
- Sarah IKHLEF
- Brahim BERKENNOU

# Première version du projet: 

- Dans cette première version, on utilise un unique serveur IRC auquel tous les
utilisateurs se connectent. 
- En interne, ce serveur va donc gérer une liste de clients et une liste de canaux.

# Execution du code:

Puisque un seul serveur est disponible:

1. En ligne de commandes :
   - Lancer le serveur : _python server.py_
   - Se connecter au serveur : > _python irc.py nickname_ 
   
2. Interface graphique:
   - Lancer le serveur : _python server.py_
   - Se connecter au serveur : > _python ircGUI.py nickname_ 
   
# Commandes implémentées:

- /away [message]
- /help 
- /invite <nick>
- /join <canal> [cle]
- /list 
- /msg [canal|nick] message 
- /names [channel]
- /quit