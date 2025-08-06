# Wazuh4j
This repository contains everything necessary for importing, visualizing and analysing the wazuh rule set.  

## Neo4j
The engine of this project is neo4j. It is a graph database perfectly tailored to this problem. 
More information about it can be found here: https://medium.com/@balajeraam/neo4j-for-beginners-a8e5a64b074a

If you want to dive into the cypher query language: https://neo4j.com/docs/cypher-manual/current/introduction/

## Usage

```
Usage: load.py [OPTIONS]

Options:
  -x, --xml-folders PATH    Folder path of xml files containing Wazuh rules.
                            It must not be an absolute path or contain
                            backtracking elements.
  -o, --ossec-configs PATH  Path to an ossec.conf file to exclude rules.
  --help                    Show this message and exit.                 
```

## Requirements to use This Project

###  Clone the repository
```
git clone https://github.com/DigiFors/Wazuh4J
cd wazuh4j
```

###  Install docker 
- Download: https://www.docker.com/get-started/

###  (Recommended) Create a Python virtual environment
```
python -m venv venv
```
- Use a virtual environment to avoid dependency conflicts

###  Install Python dependencies

```
pip install -r requirements.txt
```

###  Get the wazuh rules 
- Load the wazuh rules grouped by origin into the current directory 

> [!Warning]
> Place the rule folders in the current directory, rather than provide the absolute path to the files. 

Folder Structure - Example (The most recommended folder structure):
```
$ tree
.
├── windows-rules                                         <---
│   ├── 110000_windows_kerberos_rules.xml
│   ├── 110050_windows_ldap_rules.xml
│   ├── 110100_windows_smb_rules.xml
├── docker-compose.yml
├── import
├── init.cipher
├── load.py
├── Queries.md
├── readme.md
├── requirements.txt
├── rules                                                 <---
│   ├── 100000_wazuh-default_override_rules.xml
│   ├── 100020_own_trendmicro-apexone_rules.xml
│   ├── 100050_own_cisco-asa_additional_rules.xml
├── soc-fortress                                          <---
│   ├── 107700_windows_plug-n-play_rules.xml
│   ├── 103400_windows_taskscheduler_rules.xml
│   ├── 103300_sophos-edr_integration_rules.xml
└── wazuh-rules                                           <---
│   ├── 100300_linux_clamav_rules.xml
│   ├── 102400_forticlient_rules.xml
│   ├── 102900_checkpoint-smart1.rules.xml
```



### 1) Start the neo4j docker container

```
docker compose up
```

### 2) Load wazuh rules into the database
Run the python script: 
```
python load.py -x <path_to_folder_with_xml_files>
```

- For multiple rulesets, just add `-x <another_folder_path` for each folder. 
- If you want to specify rules excluded by ossec.conf, then add `-o <ossec_conf_path>` 

### Quick copy paste:
```
python load.py -x rules/ -o path/to/ossec.conf
```

- The *neo4j* server runs at ```http://localhost:7474```
- If you're asked for credentials, choose the *no authentification* option.
- Start exploring using *Queries.md* to find the answers to... everything!!!

Feel free to adjust the color and display text of the nodes by clicking on their label and selecting the color or a display name -> [see here](https://stackoverflow.com/questions/44674646/how-do-i-change-what-appears-on-a-node-in-neo4j).

## FAQ (Frequently Asked QUERIES)
Here are some queries which are commonly used and their SQL equivalents. 

| NEO4J                                                                       | SQL                            | Semantics                                                                           |
|-----------------------------------------------------------------------------|--------------------------------|-------------------------------------------------------------------------------------|
| `match (n) detach delete n;`                                                | `delete * from <alles>; `      | delete everything                                                                   |
| `match (n) return n ;`                                                      | `select * from <alles>; `      | get everything                                                                      |
| `match (n:LABEL) return n; `                                                | `select * from LABEL; `        | get all nodes of one type (Node label: Group, Help).                                |
| `match (n:LABEL) return n.attr1, n.attr2 ;`                                 | `select attr1,attr2 from LABEL; ` | get fields of a certain type                                                        | 
| `match (n:LABEL {name:'test'}) return n;` | `select * from LABEL where name='test' ; ` | query filter | 
| `match (n:LABEL) where n.name = 'test return n ;` | `select * from LABEL where name = 'test' ; ` | same as above |

