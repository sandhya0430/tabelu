from flask import Flask, request, jsonify
from typing import Dict, Any
import os
from dotenv import load_dotenv
import logging
from functools import partial
import os
from datetime import datetime
import json
from google.cloud import pubsub_v1
from configManager.config import TableauConfigManager
import logging
from typing import Dict
from flask_cors import CORS
import zipfile

from utils import (
    create_text_file,
    delete_gcs_folder,
    upload_folder_to_gcs,
    clear_cache_folder,
    download_file_from_gcs,
    download_gcs_folder,
    upload_to_github,
    publish_message_to_pubsub,
    load_tableau_config,
    get_view_list,
    xml_view_manipulation,
    xml_dashboard_manipulation,
    process_view
)
from client.tableau_client import download_workbook_by_name
from agents.agent import (
    view_agent,
    model_agent,
    dashboard_agent,
    structure_agent
)
from logger.logging import (
    get_logger,
    get_logs_with_filter,
    file_logger,
    get_file_logs
)

from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

logger = get_logger(__name__)

BUCKET_NAME = os.getenv('BUCKET_NAME')
LOOKER_PROJECT_ID = os.getenv('LOOKER_PROJECT_ID')
TABLEAU_BUCKET_NAME = os.getenv('TABLEAU_BUCKET_NAME')
PUBSUB_TOPIC_NAME = os.getenv('PUBSUB_TOPIC_NAME')
TABLEAU_CONFIG_FILE = os.getenv('TABLEAU_CONFIG_FILE')

tableau_details = {
    'server': 'https://10ay.online.tableau.com/',
    'credentials': {
        'username': 'elango+1@squareshift.com',
        'password': 'Squareshift!23'
    },
    'api_version': '3.20'
}

download_file_from_gcs(
            TABLEAU_BUCKET_NAME,
            "config",
            TABLEAU_CONFIG_FILE,
            TABLEAU_CONFIG_FILE
        )

tableau_config = None

tableau_config = load_tableau_config(TABLEAU_BUCKET_NAME,TABLEAU_CONFIG_FILE)
config_manager = TableauConfigManager(tableau_config,TABLEAU_BUCKET_NAME,"config",TABLEAU_CONFIG_FILE)
def create_log_context(process_id: str, workbook_name: str) -> Dict[str, str]:
    """Create a consistent log context dictionary."""
    return {
        "process_id": process_id,
        "workbook_file": workbook_name,
        "looker_project_id": LOOKER_PROJECT_ID
    }

def log_to_pubsub(message: str, process_id: str, workbook_name: str, level: str = "INFO") -> None:
    """Send logs to PubSub with consistent structure."""
    pubsub_json = {
        "process_id": process_id,
        "workbook_file": workbook_name,
        "looker_project_id": LOOKER_PROJECT_ID,
        "message": message,
        "level": level
    }
    publish_message_to_pubsub(pubsub_json, PUBSUB_TOPIC_NAME)

def process_files(xml_content: str, workbook_name: str, files_structure: Dict, log_context: Dict, process_id: str) -> None:
    """Process different types of files from the workbook."""

    if "view_files" in files_structure:
        # logger.info(f"<SPEED_METER> Processing view files. | {process_id}", extra=log_context)
        file_logger(process_id, f"<SPEED_METER> Processing view files.")
        view_content = xml_view_manipulation(xml_content)
        for file_name in view_content:
            file_content = view_agent(view_content[file_name], file_name)
            file_content = process_view(file_content, workbook_name)
            create_text_file(
                file_name, 
                "view", 
                workbook_name, 
                file_content, 
                dir=workbook_name
            )
            # logger.info(f"<SPEED_METER> View file created: {file_name}", extra=log_context)
            file_logger(process_id, f"<SPEED_METER> View file created: {file_name}")
        # for file_name in files_structure["view_files"]:
        #     view_content = xml_view_manipulation(xml_content)
        #     file_content = view_agent(view_content, workbook_name)
        #     file_content = process_view(file_content, workbook_name)
        #     create_text_file(
        #         file_name, 
        #         "view", 
        #         workbook_name, 
        #         file_content, 
        #         dir=workbook_name
        #     )
        #     # logger.info(f"<SPEED_METER> View file created: {file_name}", extra=log_context)
        #     file_logger(process_id, f"<SPEED_METER> View file created: {file_name}")

    if "model_files" in files_structure:
        # logger.info(f"<CODE_BLOCK> Processing model files. | {process_id}", extra=log_context)
        file_logger(process_id, f"<CODE_BLOCK> Processing model files.")
        for file_name in files_structure["model_files"]:
            file_content = model_agent(xml_content, workbook_name)
            create_text_file(
                f"{workbook_name}_{file_name}", 
                "model", 
                workbook_name, 
                file_content, 
                dir=workbook_name
            )
            # logger.info(f"<CODE_BLOCK> Model file created: {file_name} | {process_id}", extra=log_context)
            file_logger(process_id, f"<CODE_BLOCK> Model file created: {file_name}")

    if "dashboard_files" in files_structure:
        # logger.info(f"<DASHBOARD> Processing dashboard files  | {process_id}", extra=log_context)
        file_logger(process_id, f"<DASHBOARD> Processing dashboard files.")
        xml_dashboards = xml_dashboard_manipulation(xml_content)
        for dashboard in xml_dashboards:
            file_content = dashboard_agent(xml_dashboards[dashboard],workbook_name)
            create_text_file(
                dashboard, 
                "dashboard", 
                workbook_name, 
                file_content, 
                dir=workbook_name
            )
            # logger.info(f"<DASHBOARD> Dashboard file created: {file_name} | {process_id}", extra=log_context)
            file_logger(process_id, f"<DASHBOARD> Dashboard file created: {dashboard}")



@app.route('/api/get_logs', methods=['POST'])
def get_messages():
    """
    API endpoint to get all messages for a specific process ID from Cloud Logging.
    """
    data = request.get_json()
    process_id = data.get('process_id')

    if not process_id:
        return jsonify({
            "error": "process_id is required"
        }), 400

    try:
        # logs = get_logs_with_filter(process_id)
        # formatted_logs = []
        # seen_messages = set()  # Set to track unique messages

        # for log in logs:
        #     message = log.get("textPayload", "").split("|")[0].strip()  # Extract the message

        #     if message not in seen_messages:  # Check if message is already processed
        #         seen_messages.add(message)  # Add message to the set
        #         formatted_logs.append({
        #             "message": message,
        #             "type": log.get("severity", "INFO"),  # Extract log type (default to INFO)
        #             "timestamp": log.get("timestamp", "")  # Extract timestamp
        #         })
        formatted_logs = get_file_logs(process_id)

        return jsonify({
            "data": formatted_logs
        }), 200

    except Exception as e:
        error_message = f"Error fetching logs: {str(e)}"
        print(error_message)
        return jsonify({
            "error": error_message
        }), 500

@app.route('/api/clear_environment', methods=['GET'])
def get_clear_env():
    response, status_code = delete_gcs_folder(BUCKET_NAME, LOOKER_PROJECT_ID)
    if status_code == 200:
        download_gcs_folder(BUCKET_NAME, LOOKER_PROJECT_ID, LOOKER_PROJECT_ID)
        upload_to_github(LOOKER_PROJECT_ID)
        clear_cache_folder(LOOKER_PROJECT_ID)

    return jsonify(response), status_code

@app.route('/api/get_tableau_files', methods=['GET'])
def get_tableau_files():
    """
    API endpoint to get the list of Tableau files with their title and status.

    Returns:
        JSON: A JSON object containing the list of Tableau files with title and status or an error message.
    """
    try:
        config = load_tableau_config(TABLEAU_BUCKET_NAME, TABLEAU_CONFIG_FILE)

        if "files" in config:
            # Transform the output to match the required structure
            files = [
                {"title": file["tableau_file_name"], "status": file["Progress"]}
                for file in config["files"]
            ]
            return jsonify({"files": files}), 200
        else:
            return jsonify({"error": "Invalid configuration structure: Missing 'files' field."}), 400

    except FileNotFoundError:
        return jsonify({"error": "Configuration file not found."}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format in the configuration file."}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/api/update_tableau_config', methods=['POST'])
def update_tableau_config():
    data = request.get_json()
    config_manager.update_tableau_config(data)
    return jsonify({"message": "Tableau configuration updated successfully"}), 200

@app.route('/api/process_workbook', methods=['POST'])
def process_workbook():
    """Process a Tableau workbook and convert it to Looker format."""
    data = request.get_json()
    process_id = data.get('process_id')
    workbook_name = data.get('workbook_file')
    # logger = get_logger(__name__)
    if not workbook_name:
        error_msg = "Missing workbook_file in the request"
        # logger.error(error_msg)
        #log_to_pubsub(error_msg, process_id or "MISSING", "MISSING", "ERROR")
        return jsonify({"error": error_msg}), 400

    if not process_id:
        error_msg = "Missing process_id in the request"
        # logger.error(error_msg)
        #log_to_pubsub(error_msg, "MISSING", workbook_name, "ERROR")
        return jsonify({"error": error_msg}), 400

    if not config_manager.is_tableau_file_present(workbook_name):
        return jsonify({"message": f"workbook file : {workbook_name} in configuration file not found"}), 200

    config_manager.update_progress(workbook_name, "INPROGRESS")
    
    log_context = create_log_context(process_id, workbook_name)
    log_pubsub = partial(log_to_pubsub, process_id=process_id, workbook_name=workbook_name)

    try:
        # logger.info(f"<DOWNLOAD> Downloading {workbook_name} from GCS. | {process_id}", extra=log_context)
        file_logger(process_id, f"<DOWNLOAD> Downloading {workbook_name} from GCS.")
        log_pubsub("Downloading workbook from GCS.")
        download_file_from_gcs(
           TABLEAU_BUCKET_NAME,
           LOOKER_PROJECT_ID,
           workbook_name,
           workbook_name
        )
        workbook_base_name = workbook_name.removesuffix('.twb')
        #download_workbook_by_name(tableau_details, f"./{workbook_base_name}", workbook_base_name)

        # Logging
        file_logger(process_id, f"<RIGHT_ARROW> {workbook_name} is being processed.")

        # Check if the downloaded file is .twbx
        twbx_file = f"{workbook_base_name}.twbx"
        zip_file = f"{workbook_base_name}.zip"
        twb_file = f"{workbook_base_name}.twb"
        print(f"is path exist: {os.path.exists(twbx_file)}")
        if os.path.exists(twbx_file):
            os.rename(twbx_file, zip_file)  # Rename .twbx to .zip

            # Extract .twb file
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    print(f"hitting here:{file}")
                    if file.endswith(".twb"):
                        zip_ref.extract(file, ".")  # Extract to current directory
                        os.rename(file, twb_file)  # Rename extracted file to match expected name
                        break  # Stop after extracting the first .twb file
                    
            os.remove(zip_file)  # Delete the zip file

        # Read the .twb file
        with open(twb_file) as xml_file:
            xml_content = xml_file.read()

        # logger.info(f"<FILE_STRUCTURE> Extracting file structure. | {process_id}", extra=log_context)
        file_logger(process_id, f"<FILE_STRUCTURE> Extracting file structure.")
        log_pubsub("Extracting file structure.")
        files_structure = structure_agent(xml_content)
        files_structure = eval(files_structure[7:-3]) 
        files_structure['view_files'] = get_view_list(xml_content)
        process_files(xml_content, workbook_base_name, files_structure, log_context,process_id)
        
        # logger.info(f"<DASHBOARD> Completed Dashboard Building | {process_id}", extra=log_context)
        file_logger(process_id, f"<DASHBOARD> Completed Dashboard Building.")
        # cleanup_steps = [
        #     (f"<FLAG> Finishing up processing| {process_id}", 
        #      lambda: upload_folder_to_gcs(
        #          LOOKER_PROJECT_ID, BUCKET_NAME, 
        #          workbook_base_name, workbook_base_name
        #      )),
        #     (f"<FLAG> Completed Views, Model and Dashboards | {process_id}", 
        #      lambda: clear_cache_folder(
        #          workbook_base_name, f"{workbook_base_name}.twb"
        #      )),
        #     (f"<FLAG> Uploading to GitHub | {process_id}", 
        #      lambda: download_gcs_folder(
        #          BUCKET_NAME, LOOKER_PROJECT_ID, LOOKER_PROJECT_ID
        #      )),
        #     (f"<FINISH_FLAG> Code conversion COMPLETED for {workbook_name} | {process_id}", 
        #      lambda: upload_to_github(LOOKER_PROJECT_ID)),
        #     (f"DONE | {process_id}", 
        #      lambda: clear_cache_folder(LOOKER_PROJECT_ID))
        # ]

        cleanup_steps = [
            (f"<FLAG> Finishing up processing", 
             lambda: upload_folder_to_gcs(
                 LOOKER_PROJECT_ID, BUCKET_NAME, 
                 workbook_base_name, workbook_base_name
             )),
            (f"<FLAG> Completed Views, Model and Dashboards", 
             lambda: clear_cache_folder(
                 workbook_base_name, f"{workbook_base_name}.twb"
             )),
            (f"<FLAG> Uploading to GitHub", 
             lambda: download_gcs_folder(
                 BUCKET_NAME, LOOKER_PROJECT_ID, LOOKER_PROJECT_ID
             )),
            (f"<FINISH_FLAG> Code conversion COMPLETED for {workbook_name}", 
             lambda: upload_to_github(LOOKER_PROJECT_ID)),
            (f"DONE", 
             lambda: clear_cache_folder(LOOKER_PROJECT_ID))
        ]

        for message, operation in cleanup_steps:
            # logger.info(message, extra=log_context)
            file_logger(process_id, message)
            log_pubsub(message)
            operation()
        
        success_message = "Processing completed successfully"
        log_pubsub(success_message)
        
        config_manager.update_progress(workbook_name, "COMPLETED")
        
        return jsonify({"message": success_message,"looker_url": f"https://squareshift.cloud.looker.com/projects/{LOOKER_PROJECT_ID}"}), 200

    except Exception as e:
        error_message = f"An error occurred during processing: {str(e)}"
        # logger.error(error_message, extra=log_context)
        file_logger(process_id, error_message, type="error")
        config_manager.update_progress(workbook_name, "ERROR")
        log_pubsub(error_message, level="ERROR")
        return jsonify({"error": error_message}), 500

if __name__ == "__main__":
    app.run(debug=True)

