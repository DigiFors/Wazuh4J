import requests
import os
import sys
from neo4j import GraphDatabase
import re
from bs4 import BeautifulSoup

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "CHANGE_ME_PLEASE"

FILE_SERVER_URL = "file://"

# Get XML file list from the directory listing
def get_xml_files(path):
    xml_files = []
    for file_name in os.listdir(path):
        if file_name.lower().endswith('.xml'):
            xml_files.append(file_name)
    return xml_files

# Load XML files into Neo4j
def load_files_into_neo4j(xml_files):
    with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        with driver.session() as session:
            for xml_file in xml_files:
                xml_url = f"{FILE_SERVER_URL}{xml_file}"
                print("Loading file from", xml_url)
                cypher_query = """
                CALL apoc.load.xml($xml_url) YIELD value
                UNWIND apoc.text.split(value.name, ",") AS groupName
                MERGE (g:Group {name: groupName})
                WITH value, g
                UNWIND [c IN value._children WHERE c IS NOT NULL] AS child
                MERGE (r:Rule {
                    id:child.id,
                    level:child.level,
                    frequency: CASE WHEN child.frequency IS NOT NULL THEN child.frequency ELSE "" END,           
                    description: CASE WHEN child.description IS NOT NULL THEN child.description ELSE "" END,
                    overwrite: CASE WHEN child.overwrite IS NOT NULL THEN child.overwrite ELSE "" END
                })
                MERGE (r)-[:BELONGS]->(g)
                WITH child, r
                WITH [gr IN child._children WHERE gr._type='group'] AS groupElems, child, r
                UNWIND groupElems AS groupElem
                UNWIND apoc.text.split(groupElem._text, ",") AS groupName
                MERGE (gg:Group {name: groupName})
                MERGE (r)-[:BELONGS]->(gg)
                WITH child, r
                WITH [elem IN child._children WHERE elem._type = "if_sid" OR elem._type = "if_matched_sid"] AS elems, r, child
                UNWIND elems AS sid
                UNWIND apoc.text.split(sid._text, ",") AS ruleId
                MERGE (rr:Rule {id: ruleId})
                MERGE (rr)<-[dp:DEPENDS_ON {field: sid._type}]-(r)
                RETURN r, rr, dp;
                """
                try:
                    session.run(cypher_query, xml_url=xml_url)
                    print(f"Loaded {xml_file} into Neo4j.")
                except Exception as e:
                    print("YOOO ERROR")
                    print(e)


# Main Execution
def main():
    p = sys.argv[1]
    xml_files = get_xml_files(p)
    print("loading these files")
    print(xml_files)
    if not xml_files:
        print("No XML files found.")
        return
    load_files_into_neo4j(xml_files)

if __name__ == "__main__":
    main()