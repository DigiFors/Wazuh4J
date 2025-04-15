# Wazuh4j
This repository contains everything necessary for 1) importing 2) visualizing and 3) analysing the wazuh regelset.  

## neo4j
the database behind all this is neo4j. it is a graph database perfectly tailored to this problem. more information about it here: 

https://medium.com/@balajeraam/neo4j-for-beginners-a8e5a64b074a


### starting with docker 
to start a neo4j server using docker, exectute this command: 

```
docker run     -p 7474:7474 -p 7687:7687     --name neo4j-apoc     -e NEO4J_apoc_export_file_enabled=true     -e NEO4J_apoc_import_file_enabled=true     -e NEO4J_apoc_import_file_use__neo4j__config=true     -e NEO4J_PLUGINS=\[\"apoc\"\]     neo4j:2025.02

```