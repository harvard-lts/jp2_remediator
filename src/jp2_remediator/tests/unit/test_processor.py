import pytest
from unittest.mock import patch, MagicMock
from jp2_remediator.processor import Processor


class TestProcessor:

    @pytest.fixture
    def mock_box_reader_factory(self):
        return MagicMock()

    @pytest.fixture
    @patch("jp2_remediator.processor.configure_logger")
    def processor(self, mock_configure_logger, mock_box_reader_factory):
        mock_logger = MagicMock()
        mock_configure_logger.return_value = mock_logger
        return Processor(mock_box_reader_factory)

    def test_process_file(self, processor, mock_box_reader_factory):
        file_path = "test_file.jp2"

        # Run the processor method
        processor.process_file(file_path)

        # Test that logger.info was called once with the correct message
        processor.logger.info.assert_called_once_with(f"Processing file: {file_path}")
        mock_box_reader_factory.get_reader.assert_called_once_with(file_path)
        mock_box_reader_factory.get_reader.return_value.read_jp2_file.assert_called_once()

    @patch("os.walk", return_value=[("root", [], ["file1.jp2", "file2.jp2"])])
    def test_process_directory_with_multiple_files(self, mock_os_walk, processor, mock_box_reader_factory):
        processor.process_directory("dummy_path")

        # Test that logger.info was called for each file
        processor.logger.info.assert_any_call("Processing file: root/file1.jp2")
        processor.logger.info.assert_any_call("Processing file: root/file2.jp2")
        assert mock_box_reader_factory.get_reader.call_count == 2
        assert mock_box_reader_factory.get_reader.return_value.read_jp2_file.call_count == 2

    @patch("jp2_remediator.processor.os.path.exists", return_value=True)
    @patch("jp2_remediator.processor.boto3.client", autospec=True)
    def test_process_s3_file_with_output_key(
        self, mock_boto3_client, mock_os_path_exists, processor
    ):
        """
        When the modified file DOES exist, we expect:
        1) The logger to show 'Downloading file:' and 'Uploading modified file:'
        2) The local file path to contain a wildcard segment (file_modified_).
        3) The upload_file call to use the correct output_bucket/output_key.
        """
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client

        input_bucket = "test-bucket"
        input_key = "test-folder/file.jp2"
        output_bucket = "output-bucket"
        output_key = "output-folder/file_modified.jp2"

        # Simulate successful S3 calls
        mock_s3_client.download_file.return_value = None
        mock_s3_client.upload_file.return_value = None

        processor.process_s3_file(input_bucket, input_key, output_bucket, output_key=output_key)

        # 1. Check upload_file with a wildcard in local path
        upload_calls = [
            call
            for call in mock_s3_client.upload_file.call_args_list
            if "/tmp/file_modified_" in call.args[0]       # local path wildcard
            and call.args[1] == output_bucket
            and call.args[2] == output_key
        ]
        assert len(upload_calls) == 1, "Expected exactly one upload call with wildcard local path."

        # 2. Verify logger calls
        all_logger_msgs = [call.args[0] for call in processor.logger.info.mock_calls]
        assert any("Downloading file: test-folder/file.jp2 from bucket: test-bucket" in msg for msg in all_logger_msgs), \
            "Expected 'Downloading file:' log not found."
        assert any("Uploading modified file to bucket: output-bucket, key: output-folder/file_modified.jp2" in msg for msg in all_logger_msgs), \
            "Expected 'Uploading modified file:' log not found."

    @patch("jp2_remediator.processor.os.path.exists", return_value=False)
    @patch("jp2_remediator.processor.boto3.client", autospec=True)
    def test_process_s3_file_file_does_not_exist(
        self, mock_boto3_client, mock_os_path_exists, processor
    ):
        """
        When the modified file does NOT exist, we expect:
        1) No upload to S3 (upload_file not called).
        2) A log message stating the file does not exist, skipping upload.
        """
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client

        input_bucket = "test-bucket"
        input_key = "test-folder/file.jp2"
        output_bucket = "output-bucket"
        output_key = "output-folder/file_modified.jp2"

        mock_s3_client.download_file.return_value = None

        processor.process_s3_file(input_bucket, input_key, output_bucket, output_key=output_key)

        mock_s3_client.upload_file.assert_not_called()

        all_logger_msgs = [call.args[0] for call in processor.logger.info.mock_calls]
        assert any("does not exist, skipping upload" in msg for msg in all_logger_msgs), \
            "Expected 'skipping upload' log message not found."