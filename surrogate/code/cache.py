import json
import os
from collections import OrderedDict

CHEMIN_INDEX = "/cache/index.json"
CHEMIN_CACHE = "/cache/data"
TAILLE_CACHE = 256 * 1024 * 1024

class Cache:
    """
    Gère le cache et les index
    """
    def __init__(self):
        # Chargement (premier lancement ou index corrompu : cache vide)
        try:
            with open(CHEMIN_INDEX) as f:
                self.cache = OrderedDict(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            self.cache = OrderedDict()

        # Verifie que l'index est bien à jour vis à vis du cache à chaque lancement du script

        # Entrées dans l'index mais fichier absent du disque
        for nom in [n for n, v in self.cache.items() if not os.path.exists(v["path"])]:
            del self.cache[nom]

        # Fichiers sur le disque mais absents de l'index
        fichiers_connus = {os.path.basename(v["path"]) for v in self.cache.values()}
        for fichier in os.listdir(CHEMIN_CACHE):
            if fichier not in fichiers_connus:
                os.remove(os.path.join(CHEMIN_CACHE, fichier))

        self.used = sum(v["size"] for v in self.cache.values())
        self.save()

    def save(self):
        """
        Sauvegarde les index dans un json.
        """
        # On enregistre dans un .temp pour éviter de perdre des données en cas d'erreur
        tmp = CHEMIN_INDEX + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.cache, f)

        # On remplace le fichier.json par le .tmp juste créé
        os.replace(tmp, CHEMIN_INDEX)

    def add(self, nom, taille, tag, contenu):
        """
        Ajoute un nouveau contenu
        """
        # On enregistre pas dans le cache si la taille est trop grande
        if taille <= TAILLE_CACHE:
            # On libère la place nécessaire pour le nouveau contenu
            self.delete(taille)

            # On sauvegarde dans le cache le nouveau contenu
            chemin = CHEMIN_CACHE+"/"+nom
            with open(chemin, "wb") as f:
                f.write(contenu)

            # Mise à jour de l'index
            self.cache[nom] = {'path': chemin, "size":taille, "tag": tag}
            self.used += taille
            
            self.save()
            

    def delete(self, taille_necessaire):
        """
        Suppression avec size aware
        """
        while self.used + taille_necessaire > TAILLE_CACHE:
            _, meta = self.cache.popitem(last=False)
            self.used -= meta["size"]
            try:
                os.remove(meta["path"])
            except FileNotFoundError:
                pass

    def hit(self, nom):
        """
        LRU, lorsqu'un fichier est demandé, il repasse à la fin
        """
        self.cache.move_to_end(nom)
        self.save()

    def new_tag(self, nom, new_tag, new_size):
        """
        Met à jour le tag en cas de maj du contenu
        """
        self.cache[nom]["tag"] = new_tag
        self.cache[nom]["size"] = new_size
        self.save()

    def get(self, nom):
        """
        Renvoie le contenu en mettant à jour l'index
        """
        # Récupération des métadonnées
        meta = self.cache.get(nom)
        if meta is None: # contenu non trouvé dans l'index
            return None

        # Récupération du contenu dans le cache
        chemin = meta["path"]
        try:
            with open(chemin, 'rb') as f:
                contenu = f.read()
        except FileNotFoundError:
            # fichier disparu du disque : on retire l'entrée fantôme
            self.used -= self.cache.pop(nom)["size"]
            self.save()
            return None
        # Mise à jour de l'index
        self.hit(nom)
        return contenu
