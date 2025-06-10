# Wazuh4j
This repository contains everything necessary for 1) importing 2) visualizing and 3) analysing the wazuh rule set.  

## neo4j
The database behind all this is neo4j. It is a graph database perfectly tailored to this problem. 
More information about it here: https://medium.com/@balajeraam/neo4j-for-beginners-a8e5a64b074a

If you want to dive into the cypher query language: https://neo4j.com/docs/cypher-manual/current/introduction/

## usage
1) start the docker container `docker compose up`
    - if you're asked for credentials -> choose the no authentification option
2) Initiate a python virtual environment with `pipenv shell` and install dependencies with `pipenv update` 
3) To load wazuh rules into the database, run the python script ON THE SAME HOST AS THE DOCKER CONTAINER: `python3 load.py -x <path_to_folder_with_xml_files>`. <br> 
If you want to load xml files from multiple folders just add `-x <another_folder_path` for each folder. 
4) profit 
5) Check out Queries.md to find the answers to... eveyrthing!!!

### Quick copy paste:
```
NEO4J_URL=bolt://localhost:7687 python3 load.py -x rules/ -x ../SiemCustomWazuhRules/rules/
```
./rules sind die wazuh rules, und SiemCustomWazuhRules die gitea rules. 


use this query for testing: ` match p=(:Rule {id: "101527"})-[:DEPENDS_ON * ]->(:Rule) return p ; `

or just click on the nodes/edges/labels. you'll figure it out. 

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

### Orphaned children
**Get all nodes with a non-existent parent (the specified parent rule does not exist):**
#TODO: not working correctly
```cypher
MATCH (r:Rule)
WHERE r.parent IS NOT NULL
  AND NOT (r)-[:DEPENDS_ON {field: "parent"}]->(:Rule {id: r.parent})
RETURN r.id AS orphanRule, r.parent AS missingParent;
```

**Get all nodes with no parent specified:**
```cypher
MATCH (r:Rule) WHERE r.parent IS NULL RETURN r;
```

**Get all node pairs of rules that overwrite eachother:**
```cypher
MATCH (n)-[:OVERWRITES]->(a) RETURN a, n;
```
**Get all rule id duplicates that do not overwrite eachother:**
```cypher
MATCH (rule:Rule), (rule_duplicate:Rule) WHERE rule.id = rule_duplicate.id and not elementId(rule) = elementId(rule_duplicate) AND NOT (rule)-[:OVERWRITES]-(rule_duplicate) RETURN rule, rule_duplicate
```

here is some general introduction into neo4j 
https://medium.com/@balajeraam/neo4j-for-beginners-a8e5a64b074a
