import subprocess
import urllib.request # Pour faire une requête HTTP (surrogate devient un client de l'origin)
import urllib.error # Pour catch les error, origin éteint, 404..

# Nécessite l'installation d'arp-scan dans l'image des serveurs

# Opti : faire du multi-threading =>


def lister_surrogate():
    """
    Retourne les addresses de tous les surrogates du cluster
    """
    return subprocess.run(["arp-scan", "-I", "eth1", "-l", "-x", "-q"], capture_output=True, text=True).stdout.split()[0::2]

def ask_surrogate(address, content_name):
    """
    Demande le contenu à un surrogate du cluster à l'adresse {address}
    Le stocke dans le cache si possible
    - Parametres :
    -- address (string): address of the surrogate to reach
    - Return:
    -- if content Found, return a tuple <True, the content, the tag of the content>
    -- else, return a tuple <False, None, None>
    """
    try:
        with urllib.request.urlopen(f"http://{address}/cluster/{content_name}", timeout=10) as rep:
            contenu = rep.read()
            tag = rep.headers.get("ETag", "").strip('"')
            return contenu, tag
    except (urllib.error.URLError, OSError):
        return None, None