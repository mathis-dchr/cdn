## Entrer dans le routeur
```bash
docker exec -it <router-name> vtysh
```

## Mode configuration et paramètres globaux
```
r1# configure terminal
r1(config)# hostname <router-name>
r1(config)# ip forwarding
```

- `ip forwarding` : autorise le routeur à relayer les paquets d'une interface à une autre. Sans cette commande, BGP apprend bien les routes, mais le trafic de transit est jeté.

## Adresser les interfaces
```
r1(config)# interface <interface-name>
r1(config-if)# description vers <router-name>:<interface-name>
r1(config-if)# ip address <IP-address>/24
r1(config-if)# exit
```

## Politiques d'import/export (route-maps)
```
r1(config)# route-map RM-IN permit 10
r1(config-route-map)# exit
r1(config)# route-map RM-OUT permit 10
r1(config-route-map)# exit
```

Une route-map `permit` sans `match` laisse tout passer. Elle est **obligatoire** en eBGP sous FRR : depuis la version 7.4, FRR applique la RFC 8212. Sans politique, la session monte mais r1 n'accepte ni n'annonce aucun préfixe, et `show bgp summary` affiche `(Policy)`.

## Processus BGP et voisins
```
r1(config)# router bgp <AS>
r1(config-router)# bgp router-id 10.255.<2-first-number-AS>.<2-last-number-AS>
r1(config-router)# no bgp default ipv4-unicast
r1(config-router)# neighbor <neighbour-IP> remote-as <neighbour-AS>
r1(config-router)# neighbor <neighbour-IP> description <router-name>
```

## Famille d'adresses IPv4 unicast
```
r1(config-router)# address-family ipv4 unicast
r1(config-router-af)# network <network-address>/24
r1(config-router-af)# neighbor <neighbour-IP> activate
r1(config-router-af)# neighbor <neighbour-IP> route-map RM-IN in
r1(config-router-af)# neighbor <neighbour-IP> route-map RM-OUT out
r1(config-router-af)# exit-address-family
r1(config-router)# exit
r1(config)# exit
```

- **`network`** annonce un préfixe en BGP, **à condition qu'il existe déjà dans la table de routage** à l'identique, ici comme route connectée. C'est pour ça que les interfaces sont configurées avant.
- **`activate`** active l'échange de routes IPv4 unicast avec ce voisin. C'est nécessaire à cause de `no bgp default ipv4-unicast`.
- **`route-map ... in/out`** applique les politiques de l'étape 3.

## Sauvegarder
```
r1# write memory
```

## Vérifier
```
r1# show running-config
r1# show interface brief
r1# show bgp summary
r1# show bgp ipv4 unicast
r1# show bgp neighbors <neighbour-IP> advertised-routes
r1# show bgp neighbors <neighbour-IP> routes
r1# show ip route bgp
```
