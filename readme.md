# Wazuh4j
This repository contains everything necessary for 1) importing 2) visualizing and 3) analysing the wazuh rule set.  

## Neo4j
The engine of this project is neo4j. It is a graph database perfectly tailored to this problem. 
More information about it can be found here: https://medium.com/@balajeraam/neo4j-for-beginners-a8e5a64b074a

If you want to dive into the cypher query language: https://neo4j.com/docs/cypher-manual/current/introduction/

## Usage
1) start the docker container `docker compose up`
    - if you're asked for credentials -> choose the no authentification option
2) Initiate a python virtual environment with `pipenv shell` and install dependencies with `pipenv update` 
    - make sure to set the env variable to provide the URL to the Neo4j server!
3) To load wazuh rules into the database, run the python script: `python3 load.py -x <path_to_folder_with_xml_files>`. <br> 
If you want to load xml files from multiple folders just add `-x <another_folder_path` for each folder. 
4) Check out Queries.md to find the answers to... eveyrthing!!!

### Quick copy paste:
```
NEO4J_URL=bolt://localhost:7687 python3 load.py -x own-rules/ -x ../some-other-rules/rules/
```

Feel free to adjust the color and display text of the nodes by clicking on their Label and selecting the color or a display name -> [see here](https://stackoverflow.com/questions/44674646/how-do-i-change-what-appears-on-a-node-in-neo4j).



## FAQ (Frequently Asked QUERIES)
here are some queries which are commonly used and their SQL equivalents. 

| NEO4J                                                                       | SQL                            | Semantics                                                                           |
|-----------------------------------------------------------------------------|--------------------------------|-------------------------------------------------------------------------------------|
| `match (n) detach delete n;`                                                | `delete * from <alles>; `      | delete everything                                                                   |
| `match (n) return n ;`                                                      | `select * from <alles>; `      | get everything                                                                      |
| `match (n:LABEL) return n; `                                                | `select * from LABEL; `        | get all nodes of one type (Node label: Group, Help).                                |
| `match (n:LABEL) return n.attr1, n.attr2 ;`                                 | `select attr1,attr2 from LABEL; ` | get fields of a certain type                                                        | 
| `match (n:LABEL {name:'test'}) return n;` | `select * from LABEL where name='test' ; ` | query filter | 
| `match (n:LABEL) where n.name = 'test return n ;` | `select * from LABEL where name = 'test' ; ` | same as above | 

