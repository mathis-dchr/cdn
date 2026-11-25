# CDN

>>> -------- Tester le travail de Marion --------
>> Première installation, copie de départ du cache
mkdir C:\cache
Copy-Item -Recurse ..\cache\s1\* C:\cache\
dir C:\cache\data

>> Lancer le serveur
Dans surrogate/code : python main.py

>> Remettre à zéro du cache, état de départ
Remove-Item -Recurse C:\cache
mkdir C:\cache
Copy-Item -Recurse ..\cache\s1\* C:\cache\
python main.py

>> Check l'état
type C:\cache\index.json
dir C:\cache\data

>> Nettoyer à la fin
Remove-Item -Recurse C:\cache




>>> -------- Pour partie Origin : ----------
**---> Modifications :**
Avant, main.py ne savait qu'être un surrogate : servir ce qu'il a dans son cache ou renvoyer l'image 404.

Maintenant :
    1. Ajout de 2 outils :
    - hashlib, pour calculer l'empreinte sha256 d'un fichier
    - unquote, pour décoder les caractères spéciaux d'une URL

    2. Programme qui peut lire TYPE, PORT, FILES_DIR : programme lit la configuration via des variables d'environnement, afin d'avoir un même code pour origin et les surrogates. 
    Le yaml met TYPE: origin ou TYPE: surrogate, et le programme va adapter son comportement.

    Le cache n'est créé que pour un surrogate, l'origin n'en a pas besoin puisqu'il a directement tous les fichiers.

    3. Méthode serve_origin = comportement de l'origin :
    - Transforme l'URL en chemin de fichier
    - Check que le chemin reste bien adns le dossier de fichiers (pas lire n'imp via /../../etc/passwd)
    - Si le fichier n'existe pas, 404
    - Sinon elle lit le fichier, calcule son sha256 et renvoie le contenu avec l'ETag
    
    4. Aiguillage dans do_GET : condition au début de la requête, qui fait que si c'est un origin on appelle serve_origin, sinon on continue comme avant en mode surrogate

    5. send_error et le port : l'origin renvoie un 404 simple en texte, alors que l'image d'erreur est renvoyée par le surrogate (car face au client).
    Le port devient configurable, pour tester/lancer origin (8000) et surrogate (80) sur 1 même machine


    ETag : étiquette de version d'un contenu, ici le sha256 du fichier = empreinte qui change si un octet change. Deux fichiers identiques ont le même ETag, permet la validation, en stratégie de màj qu'on fera ensuite



**---> Tester le tout, terminaux dans surrogate\code : **
Dans files/origin, fichiers tests :
- doggo.jpeg
- shrek.jpeg
- testss.txt


Dans le terminal de lancement du serveur :
$env:TYPE = "origin"
$env:PORT = "8000"
$env:FILES_DIR = "..\files\origin"
python main.py

Ces variables d'environnement n'existent que dans le terminal où elles ont été définies. Pour revenir en mode surrogate :
Remove-Item Env:TYPE, Env:PORT, Env:FILES_DIR


Et sur le web, check 
http://localhost:8000/nimporte.png -> renvoie Error 404 classique
http://localhost:8000/shrek.jpeg -> renvoie l'image existante
http://localhost:8000/hello -> renvoie le hello programmé
http://localhost:8000/testss.txt -> renvoie le contenu du txt

Et si on teste dans le terminal avec le -i, on voit bien les infos dont le ETag (sha256 du fichier) : 
curl.exe  -i http://localhost:8000/testss.txt





>>> -------- Pour partie Read-through (surrogate qui va chercher chez l'origin) : ----------


**--> Ajout dans main.py**
1. Imports : 
   - urllib.request : le surrogate devient client HTTP de l'origin
   - urllib.error : erreurs : origin éteint, 404
   - quote  : remet les caractères spéciaux au format URL
2. ORIGIN_URL : adresse de l'origin. 
   Défaut http://localhost:8000, à adapter dans containerlab
3. Méthode  fetch_from_origin : fait un GET vers l'origin et renvoie (contenu, tag), ou (None, None) si l'origin n'a pas le fichier ou est injoignable. Le tag est l'ETag sans guillemets
4. Nouveau else dans do_GET : on cherche d'abord dans le cache
   - HIT : le fichier est en cache, on le renvoie.
   - MISS : on le demande à l'origin, on le range dans le cache (cache.add) avec son tag, puis on le renvoie. Si l'origin ne l'a pas : image 404
5. Header X-Cache : HIT ou MISS, uniquement pour voir ce qui s'est passé

Limite : seuls les fichiers à plat sont gérés, pas de sous-dossiers dans l'URL pour l'instant, todo check



**--> Tester le read-through**
Il faut 3 terminaux, tous ouverts dans surrogate\code

0. Initialisation (cache vide), serveurs arrêtés :
Remove-Item -Recurse C:\cache
mkdir C:\cache\data
Set-Content C:\cache\index.json "{}"

Ou plutôt :
Remove-Item -Recurse C:\cache
mkdir C:\cache
Copy-Item -Recurse ..\cache\s1\* C:\cache\


1. Terminal 1, l'origin :
$env:TYPE = "origin"
$env:PORT = "8000"
$env:FILES_DIR = "..\files\origin"
python main.py

2. Terminal 2, le surrogate, terminal sans variables d'environnement :
python main.py

3. Terminal 3, les tests :
    a. Premier appel, on attend "X-Cache: MISS" :
    curl.exe -s -D - -o NUL http://localhost/shrek.jpeg

    b. Vérifier que le fichier est entré dans le cache (shrek.jpeg avec son tag sha256) :
    type C:\cache\index.json
    dir C:\cache\data

    c. Deuxième appel, on attend "X-Cache: HIT" :
    curl.exe -s -D - -o NUL http://localhost/shrek.jpeg
    Dans le terminal 1 (origin), une ligne de log GET /shrek.jpeg apparaît pour le MISS et rien pour le HIT. Le surrogate a répondu seul

    d. Fichier inexistant partout, on attend un 404 avec l'image d'erreur :
    curl.exe -s -D - -o NUL http://localhost/nimporte.png

    e. Origin coupé (Ctrl+C dans le terminal 1) :
    curl.exe -s -D - -o NUL http://localhost/shrek.jpeg    # toujours HIT (en cache)
    curl.exe -s -D - -o NUL http://localhost/testss.txt    # 404 (jamais demandé, plus d'origin)

    On peut aussi tester dans le navigateur : http://localhost/shrek.jpeg

4. Nettoyer à la fin :
Remove-Item -Recurse C:\cache
+ stop les serveurs ctrl + c terminaux