import os
import shutil
from pathlib import Path

import click
from neo4j import GraphDatabase


# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "digiforss"

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
            file_copy_path = shutil.copy(file_path_obj, Path(XML_IMPORT_FOLDER, file_path_obj.name))
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
                    print(f"Loaded {xml_url} into Neo4j.")
                except Exception as e:
                    print(f"Could not load xml file to Neo4j db: {e}")


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