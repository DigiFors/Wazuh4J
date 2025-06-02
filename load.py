import os
import re
import shutil
from pathlib import Path
import click
from dotenv import load_dotenv
from neo4j import GraphDatabase
import xml.etree.ElementTree as ET

load_dotenv()

# Neo4j connection details
NEO4J_URI = os.getenv("NEO4J_URL")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

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
    # shutil.rmtree(XML_IMPORT_FOLDER)
    # os.makedirs(XML_IMPORT_FOLDER)

    for folder in folder_paths:
        # find all xml files in the folder
        xml_file_path_objs = [x.resolve() for x in Path(folder).rglob("*.xml")]
        for file_path_obj in xml_file_path_objs:
            # copy file
            print(f"Copying {str(file_path_obj)} ...")
            file_copy_path = shutil.copy(file_path_obj, Path(XML_IMPORT_FOLDER, file_path_obj.name.replace(" ", "")))

            # set permissions for linux 
            os.chmod(file_copy_path, 0o644)
            print("changed permissions...!!!")
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

            print("Load cipher database init script...")
            cypher_query_add_nodes = ""

            with open('./init.cipher', 'r') as file:
                cypher_query_add_nodes = file.read()

            for xml_file in xml_files:
                xml_url = f"{FILE_SERVER_URL}{xml_file}"
                
                print("Loading file from", xml_url)

                try:
                    result = session.run(cypher_query_add_nodes, xml_url=xml_url)
                    result.consume()
                    print(f"Loaded {xml_url} into Neo4j.")
                except Exception as e:
                    raise Exception(f"Could not load xml file {xml_url} to Neo4j db: {e}")

            # after all nodes are added, add edges
            cypher_query_add_edges = """
                    // add dependency relationships
                    MATCH (child:Rule)
                    WHERE child.parent IS NOT NULL
                    MATCH (parent:Rule {id: child.parent})
                    MERGE (child)-[:DEPENDS_ON {field: "parent"}]->(parent)
            """
            result = session.run(cypher_query_add_edges)
            result.consume()
            print(f"Connected all children with their parent nodes.")



def add_root_to_xml(xml_file):
    """
    Wraps xml file with a root element and removes illegal character &
    """

    def escape_regex_content(match):
        # matches are like "<regex*>*</regex>"
        # e.g. <regex type="pcre2">Set-.+VirtualDirectory.+?Url.+\<\w+.*\>.*?\<\/\w+\>.+?VirtualDirectory</regex>
        start_tag = match.group(1)  # start tag <regex*>
        content = match.group(2)    # content of regex node
        end_tag = match.group(3)    # end tag </regex>

        # Escape < and > inside the regex content
        content = content.replace("<", "&lt;").replace(">", "&gt;")
        return f'{start_tag}{content}{end_tag}'

    try:
        # Read the content of the file
        with open(xml_file, 'r', encoding='utf-8') as f:
            xml_content_original = f.read().strip()

        # Replace standalone & with &amp;, ignoring already-escaped entities
        xml_content = xml_content_original.replace('&', ' ')

        # escape < and > in lines "<regex*>*</regex>" (cannot be done by simple replace because we still need the brackets of the xml tags)
        xml_content = re.sub("(<regex[^>]*>)(.+?)(</regex>)", escape_regex_content, xml_content)

        # Wrap content in a root if not already rooted
        wrapped_content = f"<root>{xml_content}</root>"

        # Parse the wrapped content
        root = ET.fromstring(wrapped_content)

        # Write to a new file (or overwrite)
        tree = ET.ElementTree(root)
        tree.write(xml_file, encoding='utf-8', xml_declaration=True)
    except Exception as e:
        raise Exception(f"Add root to xml file {xml_file} failed: {e}")
    
    
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
