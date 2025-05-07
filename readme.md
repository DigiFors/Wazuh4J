# Wazuh4j
This repository contains everything necessary for 1) importing 2) visualizing and 3) analysing the wazuh regelset.  

## neo4j
the database behind all this is neo4j. it is a graph database perfectly tailored to this problem. more information about it here: 

https://medium.com/@balajeraam/neo4j-for-beginners-a8e5a64b074a


## usage
1) start the docker container `docker compose up`

    1.1) change the password for neo4j (visit http://ipaddress:7474 , creds `neo4j:neo4j`) 
    
    1.2) put the new password into the python file (`NEO4J_PASSWORD` quick and dirty FOR NOW!)
    
2) put wazuh rules into the `./import` folder 
3) initiate python `python3 -m venv venv` and `pip3 install -r requirements.txt` 
4) call python script ON THE SAME HOST AS DOCKER: `python3 load.py <path_to_import_folder>` 
5) profit 


use this query for testing: ` match p=(:Rule {id: "101527"})-[:DEPENDS_ON * ]->(:Rule) return p ; `

or just click on the nodes/edges/labels. you'll figure it out. 

## FAQ (Frequently Asked QUERIES)
here are some queries which are commonly used and their SQL equivalents. 

| NEO4J                                       | SQL                                | Semantics                                             |
|---------------------------------------------|------------------------------------|-------------------------------------------------------|
| `match (n) detach delete n;`                | `delete * from <alles> ; `         | delete everything                                     |
| `match (n) return n ;`                      | `select * from <alles> ; `         | get everything                                        |
| `match (n:LABEL) return n; `                | `select * from LABEL ; `           | get all nodes of one type (Node label: Group, Help).  |
| `match (n:LABEL) return n.attr1, n.attr2 ;` | `select attr1,attr2 from LABEL ; ` | get fields of a certain type                          |


here is some general introduciton into neo4j 
https://medium.com/@balajeraam/neo4j-for-beginners-a8e5a64b074a
