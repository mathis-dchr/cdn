'''
TODO:
- Faire documentation
'''
import os, socket
import mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler
from cache import Cache
import cluster

TYPE = os.environ.get("TYPE", "surrogate")
PORT = int(os.environ.get("PORT", 80))
DOSSIER = os.path.dirname(os.path.abspath(__file__))

# L'origin n'a pas de cache, il sert directement son dossier de fichiers
cache = Cache() if TYPE == "surrogate" else None

class H(SimpleHTTPRequestHandler):
    """
    Gère les requête HTTP vers le surrogate
    """
    def _send_content(self, type_mime, content):
        """
        Renvoie le contenu à l'utilisateur
        """
        self.send_response(200)
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        """
        Envoie le contenu demandé à l'utilisateur si trouvé
        """
        
        # Requete de la part d'un surrogate
        if self.path.startswith("/cluster"):
            # On essaye de récupérer le contenu sur le cache
            contenu = cache.get(self.path[9:]) # [9:] on enlève '/cluster/' du chemin
            if contenu is None: # Contenu non trouvé sur le cluster
                self.send_error(404)
            else:
                # Trouve le type tout seul
                type_mime = mimetypes.guess_type(self.path[9:])[0] or "application/octet-stream"

                # Renvoie le contenu au user
                self._send_content(type_mime, contenu)

        # Requete de la part d'un user
        else:
            content_name = self.path[1:] # [1:] pour enlever le premier slash
            # On récupère le contenu
            contenu = cache.get(content_name)

            # Si non présent dans le cache, on cherche dans le cluster
            if contenu is None:
                all_surrogate = cluster.lister_surrogate()
                i = 0
                while contenu is None and i < len(all_surrogate):
                    contenu, tag = cluster.ask_surrogate(all_surrogate[i], content_name)
                    i += 1
                # En théorie, on va chercher dans l'origin, pour cet exemple on renvoie une erreur
                if contenu is None:
                    self.send_error(404)
                else: # Contenu trouvé dans le cluster
                    taille = len(contenu)
                    # On rajoute le contenu dans le cache
                    cache.add(content_name, taille, tag, contenu)
                    # Trouve le type tout seul
                    type_mime = mimetypes.guess_type(content_name)[0] or "application/octet-stream"
    
                    # Renvoie le contenu au user
                    self._send_content(type_mime, contenu)
            else: # Contenu présent dans le cache
                # Trouve le type tout seul
                type_mime = mimetypes.guess_type(self.path[1:])[0] or "application/octet-stream"

                # Renvoie le contenu au user
                self._send_content(type_mime, contenu)

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