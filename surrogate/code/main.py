'''
Lancer le script avec python mickey.py
-> Sur autre terminal, tester avec curl http://localhost/hello ou http://localhost/nom_du_fichier.html --> 200 ok
-> Tester avec curl http://localhost/nom_du_fichier_inexistant.html ou http://localhost/autretexte --> 404 not found

Curl avec Hello renvoie le nom de la machine et l'ip du serveur et du client
Curl avec un fichier existant renvoie le contenu du fichier

'''
import os, socket
import mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler
from cache import Cache

cache = Cache()

DOSSIER = os.path.dirname(os.path.abspath(__file__))

class H(SimpleHTTPRequestHandler):
    """
    Gère les requête HTTP vers le surrogate
    """
    def do_GET(self):
        """
        Envoie le contenu demandé à l'utilisateur si trouvé
        """
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
        if code == 404:
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

HTTPServer(("0.0.0.0", 80), H).serve_forever()