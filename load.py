import os
import shutil
from pathlib import Path
import click
from neo4j import GraphDatabase
import xml.etree.ElementTree as ET

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "digifors123"

FILE_SERVER_URL = "file://"
XML_IMPORT_FOLDER = "./import"


def copy_xml_files_and_get_paths(folder_paths) -> list:
    """
    Copy all XML files to "./import" and return a list of the file_path_obj copy paths.
    :param folder_path: Path to the folders containing xml files
    :return: A list of paths to the file_path_obj copies
    """
    xml_file_copies = []

    # clear import folder
    shutil.rmtree(XML_IMPORT_FOLDER)
    os.makedirs(XML_IMPORT_FOLDER)

    for folder in folder_paths:
        # find all xml files in the folder
        xml_file_path_objs = [x.resolve() for x in Path(folder).rglob("*.xml")]
        for file_path_obj in xml_file_path_objs:
            # copy file
            print(f"Copying {str(file_path_obj)} ...")
            file_copy_path = shutil.copy(file_path_obj, Path(XML_IMPORT_FOLDER, file_path_obj.name.replace(" ", "")))
            add_root_to_xml(Path(XML_IMPORT_FOLDER, file_path_obj.name.replace(" ", "")))
            # store path to file copy
            xml_file_copies.append(str(Path(file_copy_path).as_posix()))
            

    return xml_file_copies


def load_files_into_neo4j(xml_files):
    """
    Load XML files into Neo4j
    :param xml_files:
    :return:
    """
    with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        with driver.session() as session:
            for xml_file in xml_files:
                xml_url = f"{FILE_SERVER_URL}{xml_file}"
                
                print("Loading file from", xml_url)
                cypher_query = """
                    CALL apoc.load.xml($xml_url) YIELD value AS root
                    UNWIND [v in root._children WHERE v._type = 'group'] as value
                    UNWIND apoc.text.split(value.name, ",") AS groupName
                    MERGE (g:Group {name: groupName})
                    WITH value, g
                    UNWIND [c IN value._children WHERE c IS NOT NULL AND c._type = "rule"] AS rule
                    MERGE (r:Rule {id: rule.id})
                    MERGE (r)-[:BELONGS]->(g)
                    WITH rule, r
                    // add the inline rule properties like frequency
                    CALL (rule, r) {
                        WITH [prop_name IN keys(rule) WHERE NOT prop_name STARTS WITH "_"] AS prop_names, rule, r
                        CALL apoc.create.setProperties(r,prop_names, [prop_name IN prop_names | rule[prop_name]]) yield node
                        RETURN node
                    }
                    WITH rule, r
                    // add group relation
                    CALL (rule, r) {
                        WITH [gr IN rule._children WHERE gr._type='group'] AS groupElems, rule, r
                        UNWIND groupElems AS groupElem
                        UNWIND apoc.text.split(groupElem._text, ",") AS groupName
                        MERGE (gg:Group {name: groupName})
                        MERGE (r)-[:BELONGS]->(gg)
                    }
                    // add description
                    CALL (rule, r) {
                        WITH [descr IN rule._children WHERE descr._type = "description"] AS descr, r, rule
                        UNWIND descr AS des
                        SET r.description = des._text
                    }
                    // add dependend rules
                    CALL (rule, r) {
                        WITH [elem IN rule._children WHERE elem._type = "if_sid" OR elem._type = "if_matched_sid"] AS elems, r, rule
                        UNWIND elems AS sid
                        UNWIND apoc.text.split(sid._text, ",") AS ruleId
                        MERGE (rr:Rule {id: ruleId})
                        MERGE (rr)<-[dp:DEPENDS_ON {field: sid._type}]-(r)
                    }
                    // add options
                    CALL (rule, r) {
                        WITH [opts IN rule._children WHERE opts._type = "options"] AS opts, r, rule
                        UNWIND opts AS opt
                        SET r.options = coalesce(r.options, []) + opt._text
                    }
                    // add fields
                    CALL (rule, r) {
                        WITH [fields IN rule._children WHERE fields._type = "field"] AS fields, r, rule
                        CALL apoc.create.setProperties(r,[field in fields | "Field: " + field.name], [field IN fields | field._text]) yield node
                        RETURN node
                    }
                    RETURN r, rule
                """
                try:
                    result = session.run(cypher_query, xml_url=xml_url)
                    result.consume()
                    print(f"Loaded {xml_url} into Neo4j.")
                except Exception as e:
                    print(f"Could not load xml file to Neo4j db: {e}")


def add_root_to_xml(xml_file):
    """
    Wraps xml file with a root element and removes illegal character &
    """
    # Read the content of the file
    with open(xml_file, 'r', encoding='utf-8') as f:
        xml_content = f.read().strip()
        
    # Replace standalone & with &amp;, ignoring already-escaped entities
    xml_content = xml_content.replace('&', ' ')

    # Wrap content in a root if not already rooted
    wrapped_content = f"<root>{xml_content}</root>"

    # Parse the wrapped content
    root = ET.fromstring(wrapped_content)

    # Write to a new file (or overwrite)
    tree = ET.ElementTree(root)
    tree.write(xml_file, encoding='utf-8', xml_declaration=True)
    
    
@click.command()
@click.option('--xml-folders', '-x', multiple=True, type=click.Path(exists=True, readable=True))
def main(xml_folders):
    print(f"Searching for XML files in {xml_folders}")
    xml_files = copy_xml_files_and_get_paths(xml_folders)

    if not xml_files:
        print("No XML files found.")
        return

    print("Loading files ino database:")
    load_files_into_neo4j(xml_files)


if __name__ == "__main__":
    main()