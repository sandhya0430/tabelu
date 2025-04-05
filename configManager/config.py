from utils import upload_file_to_gcs
import json
class TableauConfigManager:
    def __init__(self, tableau_config: dict, bucket_name: str, folder_name: str, config_file_name: str):
        """
        Initialize the TableauConfigManager with the configuration and GCS details.

        Args:
            tableau_config (dict): The JSON configuration containing the tableau files.
            bucket_name (str): The name of the GCS bucket.
            folder_name (str): The folder inside the GCS bucket.
            config_file_name (str): The name of the configuration file in the GCS bucket.
        """
        self.tableau_config = tableau_config
        self.bucket_name = bucket_name
        self.folder_name = folder_name
        self.config_file_name = config_file_name

    def _update_config_to_gcs(self):
        """
        Upload the updated configuration back to the GCS bucket.
        """
        import tempfile
        with tempfile.NamedTemporaryFile("w", delete=False) as temp_file:
            json.dump(self.tableau_config, temp_file, indent=4)
            temp_file_path = temp_file.name

        upload_file_to_gcs(self.bucket_name, self.folder_name, self.config_file_name, temp_file_path)

        # Update the local file
        with open(self.config_file_name, "w") as local_config_file:
            json.dump(self.tableau_config, local_config_file, indent=4)

    def is_tableau_file_present(self, tableau_file_name: str) -> bool:
        """
        Check if a given tableau_file_name exists in the tableau_config.

        Args:
            tableau_file_name (str): The name of the tableau file to search for.

        Returns:
            bool: True if the tableau_file_name is found, otherwise False.
        """
        if "files" not in self.tableau_config:
            return False

        for file_entry in self.tableau_config["files"]:
            if file_entry.get("tableau_file_name") == tableau_file_name:
                return True
        return False

    def update_progress(self, tableau_file_name: str, new_progress: str) -> bool:
        """
        Update the progress of a given tableau_file_name in the tableau_config.

        Args:
            tableau_file_name (str): The name of the tableau file to update.
            new_progress (str): The new progress value (e.g., COMPLETED, INPROGRESS, NOTSTARTED).

        Returns:
            bool: True if the update was successful, otherwise False.
        """
        if "files" not in self.tableau_config:
            return False

        for file_entry in self.tableau_config["files"]:
            if file_entry.get("tableau_file_name") == tableau_file_name:
                file_entry["Progress"] = new_progress
                self._update_config_to_gcs()  # Save changes to GCS
                with open(self.config_file_name, "w") as local_config_file:
                    json.dump(self.tableau_config, local_config_file, indent=4)
                return True
        return False

    def update_looker_dashboard_urls(self, tableau_file_name: str, new_urls: list) -> bool:
        """
        Update the Looker dashboard URLs of a given tableau_file_name in the tableau_config.

        Args:
            tableau_file_name (str): The name of the tableau file to update.
            new_urls (list): The new Looker dashboard URLs to add.

        Returns:
            bool: True if the update was successful, otherwise False.
        """
        if "files" not in self.tableau_config:
            return False

        for file_entry in self.tableau_config["files"]:
            if file_entry.get("tableau_file_name") == tableau_file_name:
                file_entry["Looker_dashboard_urls"] = new_urls
                with open(self.config_file_name, "w") as local_config_file:
                    json.dump(self.tableau_config, local_config_file, indent=4)
                self._update_config_to_gcs()  # Save changes to GCS
                return True
        return False

    def get_file_status(self, tableau_file_name: str) -> str:
        """
        Get the progress status of a given tableau_file_name in the tableau_config.

        Args:
            tableau_file_name (str): The name of the tableau file to get the status for.

        Returns:
            str: The progress status (e.g., COMPLETED, INPROGRESS, NOTSTARTED) or an empty string if not found.
        """
        if "files" not in self.tableau_config:
            return ""

        for file_entry in self.tableau_config["files"]:
            if file_entry.get("tableau_file_name") == tableau_file_name:
                return file_entry.get("Progress", "")
        return ""
    

    def update_tableau_config(self, data: dict) -> bool:
        """
        Update the tableau configuration with new data and upload the updated config to GCS.

        Args:
            data (dict): The new data to update in the tableau configuration.

        Returns:
            bool: True if the update and upload were successful, otherwise False.
        """
        self.tableau_config.update(data)
        self._update_config_to_gcs()
        with open(self.config_file_name, "w") as local_config_file:
            json.dump(self.tableau_config, local_config_file, indent=4)
        return True

