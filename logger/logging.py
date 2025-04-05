import os
import json
import tempfile
from google.cloud import firestore
from datetime import datetime, timezone

import logging
import google.cloud.logging
from google.cloud.logging import Client

firestore_client = firestore.Client(database="tableau2looker")
db = firestore_client.collection("logs")

class StructuredLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        context = {key: extra.get(key) for key in ["workbook_file", "looker_project_id", "process_id"] if extra.get(key)}
        return f"{msg} | Context: {context}", kwargs
    
def get_file_logs(process_id):
    doc_ref = db.document(str(process_id))
    if doc_ref.get().exists:
        doc = doc_ref.get().to_dict()
        return doc.get('data')
    else:
        return []
    
def file_logger(process_id, message, type="INFO"):
    doc_ref = db.document(str(process_id))
    if doc_ref.get().exists:
        doc = doc_ref.get().to_dict()
        data =  doc.get('data')
    else:
        data = []
    
    data.append(
        {
            "message": message,
            "type": type,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec='microseconds').replace("+00:00", "Z")
        }
    )

    doc_ref.set({"data": data})

def get_logger(name=__name__):
    client = Client()
    client.setup_logging()

    logger = logging.getLogger(name)
    if not logger.hasHandlers():  
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(name)s [%(levelname)s]: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return StructuredLoggerAdapter(logger, {})

def get_logs_with_filter(process_id):
    client = Client()
    log_filter = f'textPayload=~"{process_id}"'
    entries = []
    for entry in client.list_entries(filter_=log_filter):
        # Convert the log entry to a dictionary for JSON serialization
        entries.append(entry.to_api_repr())

    return entries
