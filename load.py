import os
import re
import shutil
import traceback
from pathlib import Path
import click
from neo4j import GraphDatabase
import xml.etree.ElementTree as ET

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"

FILE_SERVER_URL = "file://"
XML_IMPORT_FOLDER = "./import"


def copy_xml_files_and_get_paths(folder_paths, excluded_file_names=None) -> list:
    """
    Copy all XML files to "./import" and return a list of the file_path_obj copy paths.
    :param excluded_file_names: Optional list of file names to exclude.
    :param folder_path: Path to the folders containing xml files
    :return: A list of paths to the file_path_obj copies
    """
    xml_file_copies = []

    # clear import folder
    # shutil.rmtree(XML_IMPORT_FOLDER)
    # os.makedirs(XML_IMPORT_FOLDER)

    print(f"Searching for XML files in {folder_paths}")
    for folder in folder_paths:
        # find all xml files in the folder
        xml_file_path_objs = [x for x in Path(folder).rglob("*.xml")]
        for file_path_obj in xml_file_path_objs:
            if excluded_file_names is not None and file_path_obj.name in excluded_file_names:
                print(f"{file_path_obj} is excluded.")
                continue

            # copy file
            print(f"Copying {str(file_path_obj.resolve())} ...")

            subpath_in_import_folder = file_path_obj
            # remove drive letter under windows
            if file_path_obj.drive != "":
                subpath_in_import_folder = file_path_obj.relative_to(file_path_obj.drive + "/")
            # remove white spaces in path because Neo4j cannot handle that
            subpath_in_import_folder = str(subpath_in_import_folder).replace(" ", "")

            destination_file_path = Path(XML_IMPORT_FOLDER) / subpath_in_import_folder
            # create subfolders in import folder
            destination_file_path.parent.mkdir(parents=True, exist_ok=True)
            # copy xml file to the corresponding import subfolder
            file_copy_path = shutil.copy(file_path_obj, destination_file_path)

            # set permissions for linux 
            os.chmod(file_copy_path, 0o644)
            add_root_to_xml(destination_file_path)
            # store path to file copy
            xml_file_copies.append(str(Path(file_copy_path).as_posix()))

    return xml_file_copies


def get_excluded_rule_files(ossec_conf_paths):
    excluded_rule_files = []

    print(f"Collecting which rules to exclude from ossec.conf paths {ossec_conf_paths}")
    for p in ossec_conf_paths:
        with open(p, "r") as ossec_conf_file:
            ossec_conf_content = ossec_conf_file.read()

        # Example of an ossec config:
        # <ossec_config>
        #   <ruleset>
        #     <!-- Default ruleset -->
        #     <decoder_dir>ruleset/decoders</decoder_dir>
        #     <rule_dir>ruleset/rules</rule_dir>
        #     <rule_exclude>0215-policy_rules.xml</rule_exclude>
        #     <rule_exclude>0700-paloalto_rules.xml</rule_exclude> <!-- replaced by custom rules -->
        #     <decoder_exclude>0100-fortigate_decoders.xml</decoder_exclude> <!-- to be replaced by custom decoders, when ready! -->
        #     <decoder_exclude>ruleset/decoders/0051-checkpoint-smart1_decoders.xml</decoder_exclude> <!--To use custom decoder for checkpoint -->
        #     <decoder_exclude>ruleset/decoders/0505-paloalto_decoders.xml</decoder_exclude> <!--To use custom decoder for Palo Alto firewall -->
        #     <list>etc/lists/audit-keys</list>
        #     <list>etc/lists/amazon/aws-eventnames</list>
        #     <list>etc/lists/security-eventchannel</list>
        #     <!-- User-defined ruleset -->
        #     <decoder_dir>digifors_custom_rulesets/decoders</decoder_dir>
        #     <rule_dir>digifors_custom_rulesets/rules</rule_dir>
        #   </ruleset>
        # </ossec_config>

        # For each ossec block (usually only one), find all <rule_exclude> entries
        matches = re.findall(r'<rule_exclude>(.*?)</rule_exclude>', ossec_conf_content, re.DOTALL)
        excluded_rule_files.extend(match.strip() for match in matches)

    return excluded_rule_files




def load_files_into_neo4j(xml_files):
    """
    Load XML files into Neo4j
    :param xml_files:
    :return:
    """
    with GraphDatabase.driver(NEO4J_URI) as driver:
        with driver.session() as session:

            print("Load cipher database init script...")
            cypher_query_add_nodes = ""

            with open('./init.cipher', 'r') as file:
                cypher_query_add_nodes = file.read()

            for xml_file in xml_files:
                xml_url = f"{FILE_SERVER_URL}{xml_file}"
                
                print(f"Loading file from {xml_url}")

                try:
                    result = session.run(cypher_query_add_nodes, xml_url=xml_url)
                    result.consume()
                    print(f"Loaded {xml_url} into Neo4j.")
                except Exception as e:
                    raise Exception(f"Could not load xml file {xml_url} to Neo4j db: {traceback.format_exc()}")

            # after all nodes are added, add edges
            cypher_query_add_edges = """
                    // add dependency relationships
                    MATCH (child:Rule)
                    WHERE child.parents IS NOT NULL
                    UNWIND child.parents AS parent
                    MATCH (parent_node:Rule {rule_id: parent})
                    MERGE (child)-[:DEPENDS_ON {field: "parent"}]->(parent_node)
            """
            result = session.run(cypher_query_add_edges)
            result.consume()
            
            print(f"Connected all children with their parent nodes.")
            # add overwrites relation
            cypher_query_add_overwrite = """
                    MATCH (initial_rule:Rule), (overwriting_rule:Rule)
                    WHERE initial_rule.rule_id = overwriting_rule.rule_id and not elementId(initial_rule) = elementId(overwriting_rule) and  overwriting_rule.overwrite = "yes" and (initial_rule.overwrite IS NULL OR initial_rule.overwrite = "no")
                    MERGE (overwriting_rule)-[:OVERWRITES]->(initial_rule)
            
            """
            result = session.run(cypher_query_add_overwrite)
            result.consume()
            print("Added overwrites relation.")
            


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

        # Sort all children of the rule by first type and then text and then enumerate the match: match_1, match_2 ...
        for group in root.findall('group'):
            for rule in group.findall('rule'):
                matches = rule.findall('match')
                if len(matches) > 1:
                    rule[:] = sorted(rule, key = lambda child: (child.tag, child.text))
                matches = rule.findall('match')    
                for i, match in enumerate(matches, start=1):
                    match.tag = f"match_{i}"

                
        # Write to a new file (or overwrite)
        tree = ET.ElementTree(root)
        tree.write(xml_file, encoding='utf-8', xml_declaration=True)
    except Exception as e:
        raise Exception(f"Add root to xml file {xml_file} failed: {traceback.format_exc()}")

def basic_import_checks(xml_files):
    
    # simple checks using regex
    rule_count = 0
    overwrites_count = 0
    descriptions_count = 0
    for xml_file in xml_files:
        with open(xml_file, 'r', encoding='utf-8') as f:
            xml_content = f.read().strip()
            matches = re.findall(r'<rule.*?id=.*?>', xml_content)
            rule_count += len(matches)
            matches_overwrite = re.findall(r'<rule.*?overwrite=["\']yes["\'].*?>', xml_content)
            overwrites_count += len(matches_overwrite)
            matches_description = re.findall(r'<description>', xml_content)
            descriptions_count += len(matches_description)
  
    with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        with driver.session() as session:
            res = session.run("MATCH (n:Rule) RETURN COUNT(n)")
            db_rule_count = res.single().value()
            res.consume()
            res = session.run("MATCH (n:Rule) WHERE n.overwrite = 'yes' RETURN COUNT(n)")
            db_overwrites_count = res.single().value()
            res.consume()

    if rule_count != db_rule_count:
        print("!!! The rule count in the db does not match the expected rule count based on simple regex matching. This could be due to mistakes in the init.cipher.")
        print(f"!!! Rule Count Neo4j: {db_rule_count} Regex: {rule_count}")
    if overwrites_count != db_overwrites_count:
        print("!!! The rule count that have the overwrites property set in the db does not match the expected overwriting rule count based on simple regex matching. This could be due to mistakes in the init.cipher.")
        print(f"!!! Overwrite Count Neo4j: {db_overwrites_count} Regex: {overwrites_count}")


        
                


@click.command()
@click.option('--xml-folders', '-x', multiple=True, type=click.Path(exists=True, readable=True),
              help='Folder path of xml files containing Wazuh rules.')
@click.option('--ossec-configs', '-o', multiple=True, type=click.Path(exists=True, readable=True),
              help="Path to an ossec.conf file to exclude rules.")
def main(xml_folders, ossec_configs):

    # check readme for rules to exclude
    excluded_rule_files_names = get_excluded_rule_files(ossec_configs)
    xml_files = copy_xml_files_and_get_paths(xml_folders, excluded_rule_files_names)

    if not xml_files:
        print("No XML files found.")
        return

    print("Loading files ino database:")
    load_files_into_neo4j(xml_files)
    
    basic_import_checks(xml_files)
    


if __name__ == "__main__":
    main()
