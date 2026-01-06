import os
import shutil
import tempfile
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
        return reader.read_jp2_file()

    def process_directory(self, directory_path):
        """Process all JP2 files in a given directory."""
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith(".jp2"):
                    file_path = os.path.join(root, file)
                    self.process_file(file_path)

    def process_s3_file(
        self, input_bucket, input_key, output_bucket, output_key
    ):
        """
        Process a specific JP2 file from S3 and upload to a
        specified S3 location. Returns result object with output_key
        and remediation status.
        """
        s3 = boto3.client("s3")

        # Download the file from S3
        tmp_dir = tempfile.mkdtemp()
        download_path = f"/{tmp_dir}/{os.path.basename(input_key)}"
        self.logger.info(
            f"Downloading file: {input_key} from bucket: {input_bucket}"
        )
        s3.download_file(input_bucket, input_key, download_path)

        # Process the file
        reader = self.box_reader_factory.get_reader(download_path)
        result = reader.read_jp2_file()

        if result.is_skip_remediation():
            self.logger.info(f"Skipping remediation and upload for {result}.")
            return result

        modified_file_path = result.get_modified_file_path()
        if os.path.exists(modified_file_path):
            self.logger.info(
                f"Uploading modified file to bucket: {output_bucket}, "
                f"key: {output_key}"
            )
            s3.upload_file(modified_file_path, output_bucket, output_key)

            # Delete the temporary file after successful upload
            try:
                os.remove(modified_file_path)
                self.logger.debug(
                    f"Deleted temporary file: {modified_file_path}"
                )
                shutil.rmtree(tmp_dir)
                self.logger.debug(f"Deleted temporary directory: {tmp_dir}")
            except OSError as e:
                self.logger.error(
                    f"Error deleting file {modified_file_path}: {e}"
                )
        # In case the modified file was not created,
        # log a message for debugging
        else:
            self.logger.info(f"File {modified_file_path} not created.")

        return result
