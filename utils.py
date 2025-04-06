import xmltodict
import json
import os
import shutil
from google.cloud import storage
from google.cloud import pubsub_v1
from github import Github, GithubException
from dotenv import load_dotenv
from logger.logging import get_logger, file_logger
import base64
from io import BytesIO
from PIL import Image
from agents.gemini import generate_image_response_with_gemini


load_dotenv()
logger = get_logger(__name__)
connection_name = os.getenv('CONNECTION_NAME')

def generate_view_text(workbook_name):
    path = f"{workbook_name}/views"
    files = []
    for filename in os.listdir(path):
        if filename.endswith(".view.lkml") or filename.endswith(".model.lkml") or filename.endswith(".dashboard.lookml"):
            file_path = os.path.join(path, filename)
            with open(file_path, 'r') as file:
                content = file.read()
                files.append((filename, content))
    text = ""
    for filename, content in files:
        text += f"File Name: {filename}\n"
        text += content + "\n\n"
    return text

def generate_model_text(workbook_name):
    path = f"{workbook_name}/models"
    files = []
    for filename in os.listdir(path):
        if filename.endswith(".view.lkml") or filename.endswith(".model.lkml") or filename.endswith(".dashboard.lookml"):
            file_path = os.path.join(path, filename)
            with open(file_path, 'r') as file:
                content = file.read()
                files.append((filename, content))
    text = ""
    for filename, content in files:
        text += f"File Name: {filename}\n"
        text += content + "\n\n"
    return text

def load_tableu_file(xml_file_path):
    with open(xml_file_path, "r", encoding="utf-8") as file:
        xml_content = file.read()
    return xml_content

def convert_json(file_path):
    """This function takes a file path of a tableau file (.twb) and parses it to a json file"""
    xml_file = open(file_path)
    d = xmltodict.parse(xml_file.read())
    json_data = json.dumps(d, indent=4)
    with open(file_path + '.json', 'w') as json_file:
        json_file.write(json_data)

def model_include_string(model_response, worksheet_id, connection="tableau_looker_poc"):
    include_string = f"""
connection: "{connection}"
include: "/{worksheet_id}/views/*.view.lkml"
include: "/{worksheet_id}/dashboards/*.dashboard.lookml"
    """
    output_string = f"""
{include_string}
#included all views and dashboards
{model_response}
    """
    return output_string

def create_text_file(filename, filetype, worksheet_id, content, dir="looker"):
    content = content.split("```")[1]
    content = content.splitlines()[1:]
    content = "\n".join(content)
    
    if filetype == "model":
        content = model_include_string(content.strip(), worksheet_id, connection_name)

    filename = filename.lower().replace(" ", "_")

    path = {
        "model": os.path.join(dir, "models", filename if filename.endswith(".model.lkml") else filename + ".model.lkml"),
        "view": os.path.join(dir, "views", filename if filename.endswith(".view.lkml") else filename + ".view.lkml"),
        "dashboard": os.path.join(dir, "dashboards", filename if filename.endswith(".dashboard.lookml") else filename + ".dashboard.lookml"),
    }
    filepath = path.get(filetype)
    if not os.path.exists(os.path.dirname(filepath)):
        os.makedirs(os.path.dirname(filepath))
    try:
        with open(filepath, 'w') as file:
            file.write(content.strip())
        return f"File '{filename}' created successfully."
    except Exception as e:
        return f"Error creating file: {str(e)}"

def clear_cache_folder(folder_name, tablue_file=None):
    try:
        if tablue_file:
            os.remove(tablue_file)
        shutil.rmtree(folder_name)
    except OSError as e:
        logger.error("Error: %s - %s." % (e.filename, e.strerror))

def delete_gcs_folder(bucket_name, folder_name):
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        blobs = bucket.list_blobs(prefix=folder_name)

        for blob in blobs:
            blob.delete()
        
        return {"message": "clear bucket successfully"}, 200
    except Exception as e:
        return {"error": "error while clearing environment"}, 500


def download_gcs_folder(bucket_name, folder_name, destination_path):
    """
    Download an entire folder structure, including all files, from a GCS bucket.

    Args:
    - bucket_name (str): Name of the GCS bucket.
    - folder_name (str): Folder name in the bucket to download.
    - destination_path (str): Local destination path to save the folder and files.

    Returns:
    - None
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # Ensure the destination path exists
    os.makedirs(destination_path, exist_ok=True)

    # List all blobs in the folder
    blobs = client.list_blobs(bucket_name, prefix=folder_name)

    for blob in blobs:
        # Skip if the blob represents a directory
        if blob.name.endswith('/'):
            continue

        # Compute the relative file path and local file path
        relative_path = os.path.relpath(blob.name, folder_name)
        local_file_path = os.path.join(destination_path, relative_path)

        # Ensure the local directory exists
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

        # Download the blob to the local file path
        blob.download_to_filename(local_file_path)
        logger.info(f"Downloaded {blob.name} to {local_file_path}")

def download_file_from_gcs(bucket_name, folder_name, file_name, destination_path):
    """
    Download a file from a GCS bucket inside a specific folder.

    Args:
    - bucket_name (str): Name of the GCS bucket.
    - folder_name (str): Name of the folder inside the bucket.
    - file_name (str): Name of the file to download.
    - destination_path (str): Local path where the file will be saved.
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    blob_path = f"{folder_name}/{file_name}"
    blob = bucket.blob(blob_path)

    blob.download_to_filename(destination_path)

def upload_file_to_gcs(bucket_name, folder_name, file_name, source_path):
    """
    Upload a local file back to a GCS bucket inside a specific folder.

    Args:
    - bucket_name (str): Name of the GCS bucket.
    - folder_name (str): Name of the folder inside the bucket.
    - file_name (str): Name of the file to upload.
    - source_path (str): Local path of the file to upload.
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    blob_path = f"{folder_name}/{file_name}"
    blob = bucket.blob(blob_path)

    blob.upload_from_filename(source_path)
    logger.info(f"File {file_name} uploaded from {source_path} to GCS at {blob_path}")

def upload_folder_to_gcs(projectname, bucket_name, worksheet, local_folder_path):
    """
    Deletes the existing worksheet folder in GCS (if any) and uploads a local folder and its subfolders/files to a GCS bucket.

    Args:
        projectname (str): Name of the project (used as a folder in the bucket).
        bucket_name (str): Name of the GCS bucket.
        worksheet (str): Name of the worksheet (used as a subfolder under the project folder).
        local_folder_path (str): Path to the local folder to upload.
    """
    client = storage.Client()

    bucket = client.bucket(bucket_name)

    destination_folder = os.path.join(projectname, worksheet).replace("\\", "/") + "/"

    logger.info(f"Checking for existing folder: {destination_folder}")
    blobs = list(bucket.list_blobs(prefix=destination_folder))
    if blobs:
        logger.info(f"Deleting existing folder: {destination_folder}")
        for blob in blobs:
            blob.delete()
            logger.info(f"Deleted: {blob.name}")
    else:
        logger.info(f"No existing folder found for: {destination_folder}")

    logger.info(f"Uploading folder: {local_folder_path} to {destination_folder}")
    for root, dirs, files in os.walk(local_folder_path):
        for file_name in files:
            local_file_path = os.path.join(root, file_name)

            relative_path = os.path.relpath(local_file_path, local_folder_path)
            gcs_blob_path = os.path.join(destination_folder, relative_path).replace("\\", "/")

            blob = bucket.blob(gcs_blob_path)
            blob.upload_from_filename(local_file_path)
            logger.info(f"Uploaded: {local_file_path} to gs://{bucket_name}/{gcs_blob_path}")

def publish_message_to_pubsub(message, topic_name):
    """
    Usage example: 
    """
    publisher = pubsub_v1.PublisherClient()
    topic_name = 'projects/{project_id}/topics/{topic}'.format(
        project_id=os.getenv('GCP_PROJECT'),
        topic=topic_name,
    )
    message_data = json.dumps(message).encode('utf-8') if isinstance(message, dict) else message
    future = publisher.publish(topic_name, data=message_data)

def upload_to_github(local_folder_path):
    """
    Uploads a local folder and its files to a GitHub repository on a specific branch.
    Deletes any extra files or folders in the repository that are not present locally.

    Args:
        local_folder_path (str): Path to the local folder to upload.

    Environment Variables:
        GITHUB_TOKEN (str): Personal access token for GitHub authentication.
        GITHUB_REPO (str): The name of the GitHub repository (e.g., "username/repo").
        BRANCH_NAME (str): The name of the branch to upload files to.
    """
    token = os.getenv('GITHUB_TOKEN')
    repo_name = os.getenv('GITHUB_REPO')
    branch_name = os.getenv('BRANCH_NAME')

    if not token or not repo_name or not branch_name:
        logger.error("Error: Missing environment variables. Ensure GITHUB_TOKEN, GITHUB_REPO, and BRANCH_NAME are set.")
        return

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        logger.info(f"Authenticated to GitHub repository: {repo_name}")

        # Check if branch exists
        try:
            repo.get_branch(branch_name)
            logger.info(f"Branch '{branch_name}' found.")
        except GithubException:
            logger.error(f"Branch '{branch_name}' does not exist. Please create it first.")
            return

        # Get all files and folders from the GitHub repository
        def get_github_files_and_dirs(path=""):
            items = {}
            contents = repo.get_contents(path, ref=branch_name)
            for content in contents:
                if content.type == "dir":
                    items[content.path] = "dir"
                    items.update(get_github_files_and_dirs(content.path))
                else:
                    items[content.path] = "file"
            return items

        github_files_and_dirs = get_github_files_and_dirs()
        logger.info(f"Found {len(github_files_and_dirs)} files/folders in the GitHub repository.")

        # Get all files and folders from the local directory
        local_files_and_dirs = {}
        for root, dirs, files in os.walk(local_folder_path):
            for file_name in files:
                local_file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(local_file_path, local_folder_path)
                relative_path = relative_path.replace(os.path.sep, "/")  # Fix for Windows
                local_files_and_dirs[relative_path] = "file"

            for dir_name in dirs:
                relative_path = os.path.relpath(os.path.join(root, dir_name), local_folder_path)
                relative_path = relative_path.replace(os.path.sep, "/")  # Fix for Windows
                local_files_and_dirs[relative_path] = "dir"

        logger.info(f"Found {len(local_files_and_dirs)} files/folders in the local directory.")

        # Delete files/folders in GitHub that are not present locally
        for github_path, github_type in github_files_and_dirs.items():
            if github_path not in local_files_and_dirs:
                if github_type == "file":
                    repo_file = repo.get_contents(github_path, ref=branch_name)
                    repo.delete_file(repo_file.path, f"Delete {github_path}", repo_file.sha, branch=branch_name)
                    logger.info(f"Deleted file: {github_path}")
                elif github_type == "dir":
                    logger.warning(f"Extra folder detected: {github_path}. Note: GitHub API does not directly support deleting folders.")

        # Upload or update files from the local directory
        for local_path, local_type in local_files_and_dirs.items():
            if local_type == "file":
                local_file_path = os.path.join(local_folder_path, local_path)
                try:
                    with open(local_file_path, "rb") as file:  # Open in binary mode
                        content = file.read()

                    # Upload or update file in the repository
                    try:
                        repo_file = repo.get_contents(local_path, ref=branch_name)
                        repo.update_file(repo_file.path, f"Update {local_path}", content.decode("utf-8"), repo_file.sha, branch=branch_name)
                        logger.info(f"Updated: {local_path}")
                    except GithubException:
                        repo.create_file(local_path, f"Add {local_path}", content.decode("utf-8"), branch=branch_name)
                        logger.info(f"Created: {local_path}")
                except Exception as file_error:
                    logger.error(f"Error processing file '{local_path}': {file_error}")

    except GithubException as github_error:
        logger.error(f"GitHub error: {github_error}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

def get_pubsub_messages(process_id: str):
    """
    Fetch all messages from Pub/Sub for a specific process_id.
    """
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        os.getenv('GCP_PROJECT'),
        os.getenv('PUBSUB_SUBSCRIPTION_NAME')  # Use subscription name, not topic name
    )

    messages = []

    def callback(message):
        try:
            # Decode and load message data as JSON
            message_data = json.loads(message.data.decode('utf-8'))
            
            # Filter messages based on process_id
            if message_data.get('process_id') == process_id:
                messages.append({
                    "message": message_data.get('message', ''),
                    "type": message_data.get('level', 'INFO'),
                    "timestamp": message.publish_time.isoformat(),
                })
            
            # Acknowledge the message
            message.ack()
        
        except json.JSONDecodeError:
            print(f"Invalid message format: {message.data}")
            message.ack()

    # Subscribe to messages
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"Listening for messages on {subscription_path}...")

    try:
        # Keep the subscriber open for a few seconds to process messages
        streaming_pull_future.result(timeout=10)
    except Exception as e:
        streaming_pull_future.cancel()  # Cancel the subscription if an error occurs
        print(f"Error while fetching messages: {e}")

    # Sort messages by timestamp
    messages.sort(key=lambda x: x['timestamp'])

    subscriber.close()

    return messages

def load_tableau_config(TABLEAU_BUCKET_NAME,TABLEAU_CONFIG_FILE):
    """Load the Tableau configuration file from GCS."""
    try:
        download_file_from_gcs(
            TABLEAU_BUCKET_NAME,
            "config",
            TABLEAU_CONFIG_FILE,
            TABLEAU_CONFIG_FILE
        )
        with open(TABLEAU_CONFIG_FILE, "r") as file:
            tableau_config = json.load(file)
        logger.info("Tableau configuration file loaded successfully.")
        return tableau_config
    except FileNotFoundError:
        logger.error("Configuration file not found.")
        return {"error": "Configuration file not found."}
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in the configuration file.")
        return {"error": "Invalid JSON format in the configuration file."}
    except Exception as e:
        logger.error(f"An error occurred while loading the configuration file: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}
    

import xml.etree.ElementTree as ET

def handle_thumbnail(root):
    thumbnails = root.find("thumbnails")
    thumbnails_string = ET.tostring(thumbnails)
    for thumbnails in root.findall("thumbnails"):
        root.remove(thumbnails)
    return root, ET.fromstring(thumbnails_string)

def handle_dimension(root):
    worksheets = root.findall(".//worksheets")
    dashboards = root.findall(".//dashboards")

    worksheets_dimension_columns = worksheets[0].findall(".//column[@role='dimension']")
    
    if len(dashboards)>0:
        dashboards_dimension_columns = dashboards[0].findall(".//column[@role='dimension']")
        column_dimension_list = worksheets_dimension_columns + dashboards_dimension_columns
    else:
        column_dimension_list = worksheets_dimension_columns

    dimension_column_json = {}

    for column in column_dimension_list:
        if str(column.get('name')) not in dimension_column_json.keys():
            dimension_column_json[str(column.get('name'))] = column
    
    return dimension_column_json

def handle_measure(root):
    worksheets = root.findall(".//worksheets")
    dashboards = root.findall(".//dashboards")

    worksheets_measure_columns = worksheets[0].findall(".//column[@role='measure']")
    
    if len(dashboards)>0:
        dashboards_measure_columns = dashboards[0].findall(".//column[@role='measure']")
        column_measure_list = worksheets_measure_columns + dashboards_measure_columns
    else:
        column_measure_list = worksheets_measure_columns

    measure_column_json = {}

    for column in column_measure_list:
        if str(column.get('name')) not in measure_column_json.keys():
            measure_column_json[str(column.get('name'))] = column
    
    return measure_column_json

def handle_dimension_multiple(root, map_key):
    worksheets = root.findall(".//worksheets")
    dashboards = root.findall(".//dashboards")

    worksheets_dimension_columns = worksheets[0].findall(".//column[@role='dimension']")
    
    if len(dashboards)>0:
        dashboards_dimension_columns = dashboards[0].findall(".//column[@role='dimension']")
        all_column_dimension_list = worksheets_dimension_columns + dashboards_dimension_columns
    else:
        all_column_dimension_list = worksheets_dimension_columns

    column_dimension_list = []
    for i in all_column_dimension_list:
        if i.get('name') in map_key:
            column_dimension_list.append(i)

    dimension_column_json = {}

    for column in column_dimension_list:
        if str(column.get('name')) not in dimension_column_json.keys():
            dimension_column_json[str(column.get('name'))] = column
    
    return dimension_column_json

def handle_measure_multiple(root, map_key):
    worksheets = root.findall(".//worksheets")
    dashboards = root.findall(".//dashboards")

    worksheets_measure_columns = worksheets[0].findall(".//column[@role='measure']")
    
    if len(dashboards)>0:
        dashboards_measure_columns = dashboards[0].findall(".//column[@role='measure']")
        all_column_measure_list = worksheets_measure_columns + dashboards_measure_columns
    else:
        all_column_measure_list = worksheets_measure_columns

    column_measure_list = []
    for i in all_column_measure_list:
        if i.get('name') in map_key:
            column_measure_list.append(i)

    measure_column_json = {}

    for column in column_measure_list:
        if str(column.get('name')) not in measure_column_json.keys():
            measure_column_json[str(column.get('name'))] = column
    
    return measure_column_json

def get_view_list(xml_string):
    tree = ET.ElementTree(ET.fromstring(xml_string))
    root = tree.getroot()

    relations = root.findall(".//relation[@type='table']")
    view_list = [relation.get('name').strip() for relation in relations]

    return view_list

def xml_view_manipulation(xml_string):
    looker_data_type = {
        "string": "string",
        "integer": "number",
        "real": "number",
        "boolean": "yesno",
        "date": "date",
        "datetime": "date_time",
        "Year":"date_year",
        "Quarter":"date_quarter_of_year",
        "Month-Trunc":"date_month",
        "MY":"date_month",
        "MDY":"date",
        "Week":"date_week_of_year",
        "Weekday":"date_day_of_week",
        "Day":"date",
        "Quarter-Trunc": "date_quarter",
        "Year-Trunc": "date_year",
        "Day-Trunc": "date_day_of_week",
        "Month-Name": "date_month_name",
        "Month-Num": "date_month_num",
        "Quarter-Of-Year": "date_quarter_of_year",
        "Sum": "sum",
        "Count": "count",
        "CountD": "count_distinct",
        "Avg": "average",
        "Max": "max",
        "Min": "min"
    }
    tree = ET.ElementTree(ET.fromstring(xml_string))
    root = tree.getroot()
    root,_ = handle_thumbnail(root)

    collection_relations= root.findall(".//relation[@type='collection']")
    join_relations= root.findall(".//relation[@type='join']")

    relations = []
    
    if len(collection_relations)>0 or len(join_relations)>0:
        if len(collection_relations)>0:
            for collection_relation in collection_relations:  # Iterate through the list
                relations.extend(collection_relation.findall(".//relation[@type='table']"))
                relations.extend(collection_relation.findall(".//relation[@type='text']"))
        elif len(join_relations)>0:
            for join_relation in join_relations:  # Iterate through the list
                relations.extend(join_relation.findall(".//relation[@type='table']"))
                relations.extend(collection_relation.findall(".//relation[@type='text']"))
        else:
            pass

        relation_list = [ET.tostring(relation, encoding="utf-8").decode("utf-8").strip() for relation in relations]
        relations = list(dict.fromkeys(relation_list))
        
        
        view_text_list = {}
        for relation_str in relations:
            relation = ET.fromstring(relation_str)
            view_text = ""
            view_text += "<relations>\n"
            if relation.get('type') == "text":
                relation.set('looker_derived', 'yes')
                view_text += str(f"\t{ET.tostring(relation, encoding='utf-8').decode('utf-8').strip()}\n")
            else:
                view_text += f"\t{ET.tostring(relation, encoding='utf-8').decode('utf-8').strip()}\n"
            view_text += "<\\relations>\n\n"
            relation_name = relation.get('name')

            cols = root.findall(".//map[@value]")
            col_list = [ET.tostring(col, encoding='utf-8').decode('utf-8').strip() for col in cols]
            col_list = list(dict.fromkeys(col_list))

            map_key = []
            if len(col_list)>0:
                # view_text += f"{cols}\n"
                view_text += "<cols>\n"
                for col in col_list:
                    c = ET.fromstring(col)
                    if relation_name in c.get('value').split(']')[0].split('[')[1]:
                        view_text += f"\t{col}\n"
                        map_key.append(c.get('key'))
                view_text += "<\\cols>\n\n"

            dimension_column_json = handle_dimension_multiple(root, map_key)
            measure_column_json = handle_measure_multiple(root, map_key)
            # break
            
            worksheets = root.findall(".//worksheets")
            dashboards = root.findall(".//dashboards")
            
            worksheets_columns = worksheets[0].findall(".//column-instance")
            # worksheets_columns_list = [ET.tostring(column, encoding="utf-8").decode("utf-8").strip() for column in worksheets_columns]
            worksheets_columns_list = []
            for column in worksheets_columns:
                if column.get('column') in dimension_column_json:
                    col_json = dimension_column_json.get(column.get('column'))
                    column.set("role", col_json.get('role'))
                    if column.get('derivation') in looker_data_type:
                        column.set("looker_datatype", looker_data_type.get(column.get('derivation')))
                    elif col_json.get('datatype') in looker_data_type:
                        column.set("looker_datatype", looker_data_type.get(col_json.get('datatype')))
                    else:
                        pass
                elif column.get('column') in measure_column_json:
                    col_json = measure_column_json.get(column.get('column'))
                    column.set("role", col_json.get('role'))
                    if column.get('derivation') in looker_data_type:
                        column.set("looker_datatype", looker_data_type.get(column.get('derivation')))
                    elif col_json.get('datatype') in looker_data_type:
                        column.set("looker_datatype", looker_data_type.get(col_json.get('datatype')))
                    else:
                        pass
                else:
                    pass
                
                # worksheets_columns_list.append(ET.tostring(column, encoding="utf-8").decode("utf-8").strip())
                if column.get('column') in map_key:
                    worksheets_columns_list.append(column)
                    # worksheets_columns_list.append(ET.tostring(column, encoding="utf-8").decode("utf-8").strip())
            
            if len(dashboards)>0:
                dashboards_columns = dashboards[0].findall(".//column-instance")
                # dashboards_columns_list = [ET.tostring(column, encoding="utf-8").decode("utf-8").strip() for column in dashboards_columns]
                dashboards_columns_list = []
                for column in dashboards_columns:
                    if column.get('column') in dimension_column_json:
                        col_json = dimension_column_json.get(column.get('column'))
                        column.set("role", col_json.get('role'))
                        if column.get('derivation') in looker_data_type:
                            column.set("looker_datatype", looker_data_type.get(column.get('derivation')))
                        elif col_json.get('datatype') in looker_data_type:
                            column.set("looker_datatype", looker_data_type.get(col_json.get('datatype')))
                        else:
                            pass
                    elif column.get('column') in measure_column_json:
                        col_json = measure_column_json.get(column.get('column'))
                        column.set("role", col_json.get('role'))
                        if column.get('derivation') in looker_data_type:
                            column.set("looker_datatype", looker_data_type.get(column.get('derivation')))
                        elif col_json.get('datatype') in looker_data_type:
                            column.set("looker_datatype", looker_data_type.get(col_json.get('datatype')))
                        else:
                            pass
                    else:
                        pass

                    # dashboards_columns_list.append(ET.tostring(column, encoding="utf-8").decode("utf-8").strip())
                    if column.get('column') in map_key:
                        dashboards_columns_list.append(column)
                        # dashboards_columns_list.append(ET.tostring(column, encoding="utf-8").decode("utf-8").strip())
                column_list = worksheets_columns_list + dashboards_columns_list
            else:
                column_list = worksheets_columns_list
            
            column_list = worksheets_columns_list
            column_list = list(dict.fromkeys(column_list))

            col_name = []
            if len(column_list)>0:
                # view_text += f"{cols}\n"
                view_text += "<columns>\n"
                for column in column_list:
                    col_name.append(column.get('name'))
                    view_text += f"\t{ET.tostring(column, encoding='utf-8').decode('utf-8').strip()}\n"
                view_text += "<\\columns>\n\n"

            calculations = root.findall(".//calculation")
            calculation_list = []
            for calculation in calculations:
                if relation_name in c.get('value').split(']')[0].split('[')[1]:
                    calculation_list.append(ET.tostring(calculation, encoding="utf-8").decode("utf-8").strip())
            calculation_list = list(dict.fromkeys(calculation_list))
            
            if len(calculation_list)>0:
                view_text += "<calculations>\n"
                for calculation in calculation_list:
                    col_name = calculation.split(')')[0].split('(')[1]
                    for col in col_list:
                        c = ET.fromstring(col)
                        if col_name in c.get('key').split(']')[0].split('[')[1]:
                            view_text += f"\t{calculation}\n"
                view_text += "<\\calculations>\n"
                
            filters = root.findall(".//filter")
            filter_list = []
            for filter in filters:
                if filter.get('column').split('.')[1] in col_name:
                    filter_list.append(ET.tostring(filter, encoding="utf-8").decode("utf-8").strip())
            filter_list = list(dict.fromkeys(filter_list))

            if len(filter_list)>0:
                view_text += "<filters>\n"
                for filter in filter_list:
                    view_text += f"\t{filter}\n"
                view_text += "</filters>\n"
            
            view_text_list[relation_name] = view_text
        
        return view_text_list
    else:
        view_text = ""
        relations = []
        relations.extend(root.findall(".//relation[@type='table']"))
        relations.extend(root.findall(".//relation[@type='text']"))
        relation_list = [ET.tostring(relation, encoding="utf-8").decode("utf-8").strip() for relation in relations]
        relation_list = list(dict.fromkeys(relation_list))
        relation_name = ET.fromstring(relation_list[0]).get('name')
        if len(relation_list)>0:
            view_text += "<relations>\n"
            for relation_str in relation_list:
                relation = ET.fromstring(relation_str)
                if relation.get('type') == 'text':
                    relation.set('looker_derived', 'yes')
                    view_text += str(f"\t{ET.tostring(relation, encoding='utf-8').decode('utf-8').strip()}\n")
                else:
                    view_text += f"\t{relation_str}\n"
            view_text += "<\\relations>\n\n"

        cols = root.findall(".//map[@value]")
        col_list = [ET.tostring(col, encoding="utf-8").decode("utf-8").strip() for col in cols]
        col_list = list(dict.fromkeys(col_list))

        if len(col_list)>0:
            # view_text += f"{cols}\n"
            view_text += "<cols>\n"
            for col in col_list:
                view_text += f"\t{col}\n"
            view_text += "<\\cols>\n\n"

        dimension_column_json = handle_dimension(root)
        measure_column_json = handle_measure(root)
        
        worksheets = root.findall(".//worksheets")
        dashboards = root.findall(".//dashboards")
        
        worksheets_columns = worksheets[0].findall(".//column-instance")
        # worksheets_columns_list = [ET.tostring(column, encoding="utf-8").decode("utf-8").strip() for column in worksheets_columns]
        worksheets_columns_list = []
        for column in worksheets_columns:
            if column.get('column') in dimension_column_json:
                col_json = dimension_column_json.get(column.get('column'))
                column.set("role", col_json.get('role'))
                if column.get('derivation') in looker_data_type:
                    column.set("looker_datatype", looker_data_type.get(column.get('derivation')))
                elif col_json.get('datatype') in looker_data_type:
                    column.set("looker_datatype", looker_data_type.get(col_json.get('datatype')))
                else:
                    pass
            elif column.get('column') in measure_column_json:
                col_json = measure_column_json.get(column.get('column'))
                column.set("role", col_json.get('role'))
                if column.get('derivation') in looker_data_type:
                    column.set("looker_datatype", looker_data_type.get(column.get('derivation')))
                elif col_json.get('datatype') in looker_data_type:
                    column.set("looker_datatype", looker_data_type.get(col_json.get('datatype')))
                else:
                    pass
            else:
                pass

            worksheets_columns_list.append(ET.tostring(column, encoding="utf-8").decode("utf-8").strip())
        
        if len(dashboards)>0:
            dashboards_columns = dashboards[0].findall(".//column-instance")
            # dashboards_columns_list = [ET.tostring(column, encoding="utf-8").decode("utf-8").strip() for column in dashboards_columns]
            dashboards_columns_list = []
            for column in dashboards_columns:
                if column.get('column') in dimension_column_json:
                    col_json = dimension_column_json.get(column.get('column'))
                    column.set("role", col_json.get('role'))
                    if column.get('derivation') in looker_data_type:
                        column.set("looker_datatype", looker_data_type.get(column.get('derivation')))
                    elif col_json.get('datatype') in looker_data_type:
                        column.set("looker_datatype", looker_data_type.get(col_json.get('datatype')))
                    else:
                        pass
                elif column.get('column') in measure_column_json:
                    col_json = measure_column_json.get(column.get('column'))
                    column.set("role", col_json.get('role'))
                    if column.get('derivation') in looker_data_type:
                        column.set("looker_datatype", looker_data_type.get(column.get('derivation')))
                    elif col_json.get('datatype') in looker_data_type:
                        column.set("looker_datatype", looker_data_type.get(col_json.get('datatype')))
                    else:
                        pass
                else:
                    pass

                dashboards_columns_list.append(ET.tostring(column, encoding="utf-8").decode("utf-8").strip())
            column_list = worksheets_columns_list + dashboards_columns_list
        else:
            column_list = worksheets_columns_list
        
        column_list = list(dict.fromkeys(column_list))

        if len(column_list)>0:
            # view_text += f"{cols}\n"
            view_text += "<columns>\n"
            for column in column_list:
                view_text += f"\t{column}\n"
            view_text += "<\\columns>\n\n"

        calculations = root.findall(".//calculation")
        calculation_list = []
        calculation_list = [ET.tostring(calculation, encoding="utf-8").decode("utf-8").strip() for calculation in calculations]
        calculation_list = list(dict.fromkeys(calculation_list))
        
        if len(calculation_list)>0:
            view_text += "<calculations>\n"
            for calculation in calculation_list:
                view_text += f"\t{calculation}\n"
            view_text += "<\\calculations>\n"

        filters = root.findall(".//filter")
        filter_list = [ET.tostring(filter, encoding="utf-8").decode("utf-8").strip() for filter in filters]
        filter_list = list(dict.fromkeys(filter_list))

        if len(filter_list)>0:
            view_text += "<filters>\n"
            for filter in filter_list:
                view_text += f"\t{filter}\n"
            view_text += "</filters>\n"

        return {relation_name: view_text}

def xml_layout_manipulation(worksheet_names, dashboard):
    zones = {}

    for zone in dashboard.findall(".//zone"):
        if zone.get('name') in worksheet_names and zone.get("param", None) == None:
            zones[zone.get('name')] = [int(zone.get('x')), int(zone.get('y'))]
    
    x = set()
    y = set()
    for zone in zones:
        x.add(zones[zone][0])
        y.add(zones[zone][1])
    
    x = list(x)
    y = list(y)
    x.sort()
    y.sort()
    layout_dashboard = [[] for _ in range(len(y))]
    for zone in zones:
        row_index = y.index(zones[zone][1])
        rows = layout_dashboard[row_index]
        if len(rows)==0:
            layout_dashboard[row_index].append(zone)
        else:
            inserted = False
            for i, row in enumerate(rows):
                if zones[row][0] > zones[zone][0]:  # Corrected comparison and variable name
                    layout_dashboard[row_index].insert(i, zone)  # Corrected insert call
                    inserted = True
                    break
            if not inserted:
                layout_dashboard[row_index].append(zone)
    
    layout = """
    layout: grid
    rows:
"""
    for i in layout_dashboard:
        layout+=f"\t- elements: [{', '.join(i)}]\n\theight: N\n"

    return layout_dashboard

def resize_image(image_data, max_size=(500, 500)): # Example max size
    """Resizes an image to fit within max_size."""
    try:
        img = Image.open(BytesIO(base64.b64decode(image_data))) # Decode base64 first to get binary data.
        img.thumbnail(max_size)  # Resize while maintaining aspect ratio
        buffered = BytesIO()
        img.save(buffered, format="PNG")  # Save resized image to buffer
        return base64.b64encode(buffered.getvalue()).decode("utf-8") # Return new base64 string
    except Exception as e:
        print(f"Error resizing image: {e}")
        return None

def get_chart_type(name, thumbnails):
    thumbnail = thumbnails.find(f".//thumbnail[@name='{name}']")
    img_64 = thumbnail.text

    resized_img_64 = resize_image(img_64)  # Resize using the function from previous response
    if resized_img_64:
        response = generate_image_response_with_gemini(resized_img_64)
        response = eval(response[7:-3])
    else:
        response = None

    return response

def xml_dashboard_manipulation(xml_string):
    try:
        tree = ET.ElementTree(ET.fromstring(xml_string))
        root = tree.getroot()
    except ET.ParseError as e:
        raise e

    root, thumbnails = handle_thumbnail(root)

    final_dashboard_list = {}

    dashboard_list = root.findall(".//dashboard")
    if len(dashboard_list) > 0:
        dashboards = root.find(".//dashboards")
        root.remove(dashboards)
        for dashboard in dashboard_list:
            dashboards.remove(dashboard)


        worksheet_dict = {}
        worksheets = root.find(".//worksheets")
        root.remove(worksheets)
        for worksheet in worksheets.findall(".//worksheet"):
            result_json = get_chart_type(worksheet.get("name"), thumbnails)
            if result_json:
                worksheet.set("looker_chart_type", result_json['looker_type'])
                # worksheet.set("generic_chart_type", result_json['name'])
                if result_json['stacked_type'] != 'No':
                    worksheet.set("stacked_type", result_json['stacked_type'])
            worksheet_dict[worksheet.get("name")] = worksheet
            worksheets.remove(worksheet)
        
        root_string = ET.tostring(root)
        worksheet_string = ET.tostring(worksheets)
        dashboard_string = ET.tostring(dashboards)

        for dashboard in dashboard_list:
            root_temp = ET.fromstring(root_string)
            worksheet_temp = ET.fromstring(worksheet_string)
            dashboard_temp = ET.fromstring(dashboard_string)
            dashboard_name = dashboard.get('name')
            layout = xml_layout_manipulation(list(worksheet_dict.keys()), dashboard)

            for zone in dashboard.findall(".//zone"):
                if zone.get('name') in worksheet_dict:
                    if zone.get('param', None) == None:
                        worksheet_temp.append(worksheet_dict[zone.get('name')])
            dashboard_temp.append(dashboard)

            root_temp.append(worksheet_temp)
            root_temp.append(dashboard_temp)

            final_dashboard_list[dashboard.get('name')] = ET.tostring(root_temp, encoding="utf-8").decode("utf-8").strip() + f"\n\nDashboard Name: {dashboard_name}\n\nuse this layout for looker dashboards\n\n{layout}"
        return final_dashboard_list
    else: 
        return {"dashboard": root}

def process_view(view_content, workbook_name):
    view = """
```view
view: aaa_map {
    sql_table_name: `elastic-pocs.pixel_perfect.aaa_map` ;;

    dimension: date {
        description: "Monthly date derived from the DATE field"
        type: date
        sql: ${TABLE}.DATE ;;
    }

    dimension: city {
        type: string
        sql: ${TABLE}.CITY ;;
    }

    dimension: country {
        type: string
        sql: ${TABLE}.COUNTRY ;;
    }

    dimension: state {
        type: string
        sql: ${TABLE}.STATE ;;
    }

    dimension: date_quarter_of_year {
        description: "Quarterly date derived from the DATE field"
        type: date_quarter_of_year
        sql: ${TABLE}.DATE ;;
    }

    dimension: date_year {
        description: "Yearly date derived from the DATE field"
        type: date_year
        sql: ${TABLE}.DATE ;;
    }

    dimension: date_month {
        description: "Month date derived from the DATE field"
        type: date_month
        sql: ${TABLE}.DATE ;;
    }

    measure: value_sum {
        type: sum
        sql: ${TABLE}.VALUE ;;
    }
}
```
"""

    if "Country_Data_Dashboard" in workbook_name:
        return view
    else:
        return view_content