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
from urllib.parse import unquote

TYPE = os.environ.get("TYPE", "surrogate")
PORT = int(os.environ.get("PORT", 80))
FILES_DIR = os.environ.get("FILES_DIR", "/files")

# L'origin n'a pas de cache, il sert directement son dossier de fichiers
cache = Cache() if TYPE == "surrogate" else None

DOSSIER = os.path.dirname(os.path.abspath(__file__))

class H(SimpleHTTPRequestHandler):
    """
    Gère les requête HTTP vers le surrogate
    """

    def servir_origin(self):
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
            return self.servir_origin() # Le reste va à servir_origin, la route /add de test n'existe plus côté origin
    
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
            # On récupère le contenu => [1:] pour enlever le premier slash
            contenu = cache.get(self.path[1:])
            if contenu is None:
                self.send_error(404)
            else:
                # Trouve le type tout seul
                type_mime = mimetypes.guess_type(self.path[1:])[0] or "application/octet-stream"

                # Renvoie le contenu au user
                self.send_response(200)
                self.send_header("Content-Type", type_mime)
                self.send_header("Content-Length", str(len(contenu)))
                self.end_headers()
                self.wfile.write(contenu)


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