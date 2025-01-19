import datetime
import os
import boto3
from jp2_remediator import configure_logger


class Processor:
    """Class to process JP2 files."""

    def __init__(self, factory):
        """Initialize the Processor with a BoxReader factory."""
        self.box_reader_factory = factory
        self.logger = configure_logger(__name__)

    def process_file(self, file_path):
        """Process a single JP2 file."""
        self.logger.info(f"Processing file: {file_path}")
        reader = self.box_reader_factory.get_reader(file_path)
        reader.read_jp2_file()

    def process_directory(self, directory_path):
        """Process all JP2 files in a given directory."""
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith(".jp2"):
                    file_path = os.path.join(root, file)
                    self.process_file(file_path)

    def process_s3_file(self, input_bucket, input_key, output_bucket, output_key):
        """Process a specific JP2 file from S3 and upload to a specified S3 location."""
        s3 = boto3.client("s3")

        # Download the file from S3
        download_path = f"/tmp/{os.path.basename(input_key)}"
        self.logger.info(f"Downloading file: {input_key} from bucket: {input_bucket}")
        s3.download_file(input_bucket, input_key, download_path)

        # Process the file
        reader = self.box_reader_factory.get_reader(download_path)
        reader.read_jp2_file()

        if hasattr(reader, "skip_remediation") and reader.skip_remediation:
            self.logger.info(
                f"Skipping upload for {download_path} because curv_trc_gamma_n != 1 for at least one TRC channel."
            )
            return

        # Generate the modified file path, use timestamp if output_key is not provided
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        modified_file_path = download_path.replace(".jp2", f"_modified_{timestamp}.jp2")

        if os.path.exists(modified_file_path):
            self.logger.info(f"Uploading modified file to bucket: {output_bucket}, key: {output_key}")
            s3.upload_file(modified_file_path, output_bucket, output_key)

            # Delete the temporary file after successful upload
            try:
                os.remove(modified_file_path)
                self.logger.info(f"Deleted temporary file: {modified_file_path}")
            except OSError as e:
                self.logger.error(f"Error deleting file {modified_file_path}: {e}")
        # In case the modified file was not created, log a message for debugging
        else:
            self.logger.info(f"File {modified_file_path} not created.")
