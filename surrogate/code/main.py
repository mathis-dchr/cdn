'''
Lancer le script avec python mickey.py
-> Sur autre terminal, tester avec curl http://localhost/hello ou http://localhost/nom_du_fichier.html --> 200 ok
-> Tester avec curl http://localhost/nom_du_fichier_inexistant.html ou http://localhost/autretexte --> 404 not found

Curl avec Hello renvoie le nom de la machine et l'ip du serveur et du client
Curl avec un fichier existant renvoie le contenu du fichier

'''
import os, socket, hashlib
import mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler
from cache import Cache
from urllib.parse import unquote, quote # Gére rles caractères spéciaux au format URL
import urllib.request # Pour faire une requête HTTP (surrogate devient un client de l'origin)
import urllib.error # Pour catch les error, origin éteint, 404..

TYPE = os.environ.get("TYPE", "surrogate")
PORT = int(os.environ.get("PORT", 80))
FILES_DIR = os.environ.get("FILES_DIR", "/files")

# Adresse de l'origin, pour que le surrogate sache à qui demander les fichiers qu'il n'a pas
# En local sur le PC, phase de test, localhost:8000. Dans containerlab : http://20.40.1.2 ? Todo, check
ORIGIN_URL = os.environ.get("ORIGIN_URL", "http://localhost:8000")

# L'origin n'a pas de cache, il sert directement son dossier de fichiers
cache = Cache() if TYPE == "surrogate" else None

DOSSIER = os.path.dirname(os.path.abspath(__file__))

class H(SimpleHTTPRequestHandler):
    """
    Gère les requête HTTP vers le surrogate
    """
    def fetch_from_origin(self, nom):
        """
        Demande le fichier à l'origin
        Renvoie (contenu, tag) si l'origin l'a, ou (None, None) sinon
        """
        try:
            # Comme un navigateur, un GET vers l'origin
            with urllib.request.urlopen(f"{ORIGIN_URL}/{quote(nom)}", timeout=10) as rep:
                contenu = rep.read() # Le fichier
                tag = rep.headers.get("ETag", "").strip('"') # Son ETag sans les guillemets
        except (urllib.error.URLError, OSError):
            # 404 (l'origin n'a pas le fichier) ou origin éteint/injoignable : dans les deux cas on abandonne
            return None, None
        return contenu, tag

    def serve_origin(self):
        """
        Comportement de l'origin : sert un fichier de FILES_DIR avec son ETag (sha256), ou 404 simple
        """
        # Nom demandé, sans le "/" initial ni les ?query, et sans possibilité de sortir du dossier avec ../
        nom = unquote(self.path.split("?")[0]).lstrip("/")
        racine = os.path.abspath(FILES_DIR)
        chemin = os.path.abspath(os.path.join(racine, nom))
        if not chemin.startswith(racine + os.sep) or not os.path.isfile(chemin):
            return self.send_error(404)

        with open(chemin, "rb") as f:
            contenu = f.read()

        tag = hashlib.sha256(contenu).hexdigest()
        type_mime = mimetypes.guess_type(chemin)[0] or "application/octet-stream"

        self.send_response(200)
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(contenu)))
        self.send_header("ETag", f'"{tag}"')
        self.end_headers()
        self.wfile.write(contenu)
    
    def do_GET(self):
        """
        Envoie le contenu demandé à l'utilisateur si trouvé
        """
        if TYPE == "origin" and self.path != "/hello": # Garder /hello dispo sur l'origin pour check qu'il tourne. Le surrogate passe à côté de ce if
            return self.serve_origin() # Le reste va à serve_origin, la route /add de test n'existe plus côté origin
    
        if self.path == "/hello": # Si chemin demandé = hello, renvoie ce qui suit, du contenu fabriqué et non pas le contenu d'un fichier
            msg = (f"Hello world from {socket.gethostname()} "
                   f"(ip serveur {self.connection.getsockname()[0]}, "
                   f"client {self.client_address[0]})\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
        # Teste l'ajout de fichier à refaire par la suite
        elif self.path == "/add":
            # Ajoute le fichier test_del.png pour tester la fonction add et delete de cache.py
            with open(os.path.join(DOSSIER, "test_del.png"), "rb") as f:
                contenu = f.read()
            cache.add("test_del.jpg", 250 * 1024 * 1024, "tagtest", contenu)   # taille truquée : 100 Mo
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ajoute\n")
        else:
            # Nom du fichier, sans le "/" initial, sans les ?options et décodé
            nom = unquote(self.path.split("?")[0]).lstrip("/")

            # On ne gère que des fichiers à plat, pas de sous-dossiers pour l'instant, todo après
            if nom == "" or "/" in nom:
                return self.send_error(404)

            etat = "HIT" # On suppose qu'on l'a déjà
            contenu = cache.get(nom)

            if contenu is None: # Si on ne l'a pas --> MISS
                etat = "MISS"
                contenu, tag = self.fetch_from_origin(nom)
                if contenu is None: # L'origin non plus, ou il est éteint -> 404
                    return self.send_error(404)
                # Rangé dans le cache pour la prochaine fois
                cache.add(nom, len(contenu), tag, contenu)

            # On renvoie le contenu au client, avec un header qui dit HIT ou MISS
            type_mime = mimetypes.guess_type(nom)[0] or "application/octet-stream" # Trouve le type tout seul
            self.send_response(200)
            self.send_header("Content-Type", type_mime)
            self.send_header("Content-Length", str(len(contenu)))
            self.send_header("X-Cache", etat)
            self.end_headers()
            self.wfile.write(contenu) # Renvoie le contenu au user


    def send_error(self, code, message=None, explain=None):
        """
        Envoie une image d'erreur
        """
        if code == 404 and TYPE == "surrogate" : # Origin renvoie 404 classique, seul le surrogate renvoie l'image d'erreur
            try:
                with open("404PasImage.png", "rb") as f:  # relatif à www grâce au os.chdir
                    data = f.read()
            except OSError:
                return super().send_error(code, message, explain)  # image absente : 404 classique
            self.send_response(404)  # on garde bien le code 404
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
        else:
            super().send_error(code, message, explain)

HTTPServer(("0.0.0.0", PORT), H).serve_forever()