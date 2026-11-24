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
---> Modifications :
Avant, main.py ne savait qu'être un surrogate : servir ce qu'il a dans son cache ou renvoyer l'image 404.

Maintenant :
    1. Ajout de 2 outils :
    - hashlib, pour calculer l'empreinte sha256 d'un fichier
    - unquote, pour décoder les caractères spéciaux d'une URL

    2. Programme qui peut lire TYPE, PORT, FILES_DIR : programme lit la configuration via des variables d'environnement, afin d'avoir un même code pour origin et les surrogates. 
    Le yaml met TYPE: origin ou TYPE: surrogate, et le programme va adapter son comportement.

    Le cache n'est créé que pour un surrogate, l'origin n'en a pas besoin puisqu'il a directement tous les fichiers.

    3. Méthode servir_origin = comportement de l'origin :
    - Transforme l'URL en chemin de fichier
    - Check que le chemin reste bien adns le dossier de fichiers (pas lire n'imp via /../../etc/passwd)
    - Si le fichier n'existe pas, 404
    - Sinon elle lit le fichier, calcule son sha256 et renvoie le contenu avec l'ETag
    
    4. Aiguillage dans do_GET : condition au début de la requête, qui fait que si c'est un origin on appelle servir_origin, sinon on continue comme avant en mode surrogate

    5. send_error et le port : l'origin renvoie un 404 simple en texte, alors que l'image d'erreur est renvoyée par le surrogate (car face au client).
    Le port devient configurable, pour tester/lancer origin (8000) et surrogate (80) sur 1 même machine


    ETag : étiquette de version d'un contenu, ici le sha256 du fichier = empreinte qui change si un octet change. Deux fichiers identiques ont le même ETag, permet la validation, en stratégie de màj qu'on fera ensuite



---> Tester le tout, terminaux dans surrogate\code : 
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

