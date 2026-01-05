import unittest
import os
from unittest.mock import patch, MagicMock
from jp2_remediator.in_memory_box_reader import InMemoryBoxReader
from jpylyzer import boxvalidator
from project_paths import paths

# Define the path to the test data file
TEST_DATA_PATH = os.path.join(paths.dir_unit_resources, "sample.jp2")


class TestInMemoryBoxReader(unittest.TestCase):

    def setUp(self):
        # Read the sample file into memory
        with open(TEST_DATA_PATH, "rb") as f:
            self.test_image_bytes = f.read()

        # Set up an InMemoryBoxReader instance for each test
        self.reader = InMemoryBoxReader(self.test_image_bytes)
        self.reader.logger = MagicMock()  # Mock logger directly

    # Test for initialization with bytes
    def test_initialization_with_bytes(self):
        # Test that InMemoryBoxReader initializes correctly with bytes
        reader = InMemoryBoxReader(b"test content")
        self.assertEqual(reader.file_path, "::memory::")
        self.assertIsInstance(reader.file_contents, bytes)
        self.assertEqual(reader.file_contents, b"test content")

    # Test for initialize_validator method
    def test_initialize_validator_with_file_content(self):
        # Initialize validator and check the type
        validator = self.reader.initialize_validator()
        self.assertIsInstance(validator, boxvalidator.BoxValidator)

    # Test for find_box_position method
    def test_find_box_position_in_file(self):
        # Find a known box position in the sample file
        position = self.reader.find_box_position(b"\x6a\x70\x32\x68")
        self.assertNotEqual(position, -1)  # Ensure that the box is found

    # Test for check_boxes method
    def test_check_boxes_in_file(self):
        # Call check_boxes
        header_offset_position = self.reader.check_boxes()
        self.assertIsNotNone(header_offset_position)

    # Test for process_colr_box method
    def test_process_colr_box_in_file(self):
        # Find the colr box position
        colr_position = self.reader.find_box_position(b"\x63\x6f\x6c\x72")
        if colr_position == -1:
            self.fail("'colr' box not found in the test file.")

        # Process the colr box
        header_offset_position = self.reader.process_colr_box(colr_position)
        self.assertIsNotNone(header_offset_position)

    # Test for remediate_jp2 method returns tuple
    def test_remediate_jp2_returns_tuple(self):
        # Call remediate_jp2 and verify it returns a tuple
        result = self.reader.remediate_jp2()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        jp2_result, remediated_bytes = result
        self.assertIsNotNone(jp2_result)
        self.assertIsInstance(remediated_bytes, (bytes, bytearray))

    # Test for process_all_trc_tags method
    def test_process_all_trc_tags(self):
        # Create TRC tags to process
        trc_tags = (
            b"\x72\x54\x52\x43" + b"\x67\x54\x52\x43" + b"\x62\x54\x52\x43"
        )
        self.reader.file_contents = bytearray(
            b"\x00" * 50 + trc_tags + b"\x00" * 50
        )
        header_offset_position = 50
        modified_contents = self.reader.process_all_trc_tags(
            header_offset_position
        )
        self.assertEqual(modified_contents, self.reader.file_contents)

    # Test for check_boxes method logging when 'jp2h' not found
    def test_jp2h_not_found_logging(self):
        # Set up file_contents to simulate a missing 'jp2h' box
        self.reader.file_contents = bytearray(b"\x00" * 100)
        # Arbitrary content without 'jp2h'
        # Call the method that should log the debug message
        self.reader.check_boxes()
        # Check that the specific debug message was logged
        self.reader.logger.debug.assert_any_call(
            "'jp2h' not found in the file."
        )

    # Test for remediate_jp2 method when content is empty
    def test_remediate_jp2_empty_content(self):
        # Create reader with empty bytes
        reader = InMemoryBoxReader(b"")
        result, remediated_bytes = reader.remediate_jp2()

        # Should return empty result and empty bytes
        self.assertEqual(result.path, "::memory::")
        self.assertEqual(remediated_bytes, b"")

    # Test for process_colr_box method when meth_value == 1
    def test_process_colr_box_meth_value_1(self):
        # Create file contents with exactly positioned
        # 'colr' box and meth_value = 1
        # Ensure 'colr' starts at 100, followed by 4 bytes,
        # and then meth_value at 1
        self.reader.file_contents = bytearray(
            b"\x00" * 100  # Padding before 'colr' box
            + b"\x63\x6f\x6c\x72"  # 'colr' box
            + b"\x01"  # meth_value set to 1
        )
        colr_position = 100
        header_offset_position = self.reader.process_colr_box(colr_position)
        expected_position = colr_position + 4 + 7
        # Assert the expected header offset position
        self.assertEqual(header_offset_position, expected_position)
        self.reader.logger.debug.assert_any_call(
            "'meth' is 1, setting header_offset_position to: "
            f"{expected_position}"
        )

    # Test for process_colr_box method with unrecognized meth_value
    def test_process_colr_box_unrecognized_meth_value(self):
        self.reader.file_contents = bytearray(
            b"\x00" * 100  # Padding before 'colr' box
            + b"\x63\x6f\x6c\x72"  # 'colr' box
            + b"\x03"  # meth_value set to 3
        )
        colr_position = 100
        header_offset_position = self.reader.process_colr_box(colr_position)
        self.assertIsNone(header_offset_position)
        self.reader.logger.debug.assert_any_call(
            "'meth' value 3 is not recognized (must be 1 or 2)."
        )

    # Test for process_colr_box method when 'colr' box is missing
    def test_process_colr_box_missing(self):
        self.reader.file_contents = bytearray(b"\x00" * 100)
        colr_position = -1
        header_offset_position = self.reader.process_colr_box(colr_position)
        self.assertIsNone(header_offset_position)
        self.reader.logger.debug.assert_any_call(
            "'colr' not found in the file."
        )

    # Test for process_trc_tag method with incomplete trc_tag_entry
    def test_process_trc_tag_incomplete_entry(self):
        # Prepare the test data
        self.reader.file_contents = bytearray(
            b"\x00" * 100 + b"\x72\x54\x52\x43" + b"\x00" * 6
        )
        trc_hex = b"\x72\x54\x52\x43"  # Hex for 'rTRC'
        header_offset_position = 50
        original_contents = bytearray(self.reader.file_contents)

        # Call the method under test
        new_contents = self.reader.process_trc_tag(
            trc_hex, "rTRC", original_contents, header_offset_position
        )

        # Assert that the appropriate debug message was logged
        expected_message = (
            "Could not extract the full 12-byte 'rTRC' tag entry."
        )
        self.reader.logger.debug.assert_any_call(expected_message)

        # Assert that new_contents is unchanged
        self.assertEqual(new_contents, original_contents)

    # Test for process_trc_tag: trc_hex not found in new_contents
    def test_process_trc_tag_trc_hex_not_found(self):
        # Prepare the test data for when trc_hex is not found
        trc_hex = b"\x72\x54\x52\x43"  # Hex value not present in new_contents
        trc_name = "rTRC"
        new_contents = bytearray(
            b"\x00" * 100
        )  # Sample contents without trc_hex
        header_offset_position = 50

        # Call process_trc_tag and expect no modifications to new_contents
        result = self.reader.process_trc_tag(
            trc_hex, trc_name, new_contents, header_offset_position
        )

        # Check that the function returned the original new_contents
        self.assertEqual(result, new_contents)

        # Verify that the correct debug message was logged
        self.reader.logger.debug.assert_any_call(
            f"'{trc_name}' not found in the file."
        )

    # Test for process_trc_tag: header_offset_position is None
    def test_process_trc_tag_header_offset_none(self):
        # Prepare the test data where header_offset_position is None
        trc_hex = b"\x72\x54\x52\x43"  # Hex value found in new_contents
        trc_name = "rTRC"
        new_contents = bytearray(b"\x00" * 50 + trc_hex + b"\x00" * 50)
        header_offset_position = None  # Simulate unrecognized meth value

        # Call process_trc_tag and expect no modifications to new_contents
        result = self.reader.process_trc_tag(
            trc_hex, trc_name, new_contents, header_offset_position
        )

        # Check that the function returned the original new_contents
        self.assertEqual(result, new_contents)

        # Verify that the correct debug message was logged
        self.reader.logger.debug.assert_any_call(
            f"Cannot calculate 'curv_{trc_name}_position' "
            f"due to an unrecognized 'meth' value."
        )

    # Test for remediate_jp2 method when file_contents is valid
    def test_remediate_jp2_with_valid_content(self):
        # Prepare the test data with valid file contents
        self.reader.file_contents = bytearray(b"Valid JP2 content")

        # Mock dependent methods and attributes
        with (
            patch.object(
                self.reader, "initialize_validator"
            ) as mock_initialize_validator,
            patch.object(self.reader, "validator") as mock_validator,
            patch.object(self.reader, "check_boxes") as mock_check_boxes,
            patch.object(
                self.reader, "process_all_trc_tags"
            ) as mock_process_all_trc_tags,
        ):

            # Set up the mock for validator._isValid()
            mock_validator._isValid.return_value = True

            # Set up return values for other methods
            mock_check_boxes.return_value = (
                100  # Example header_offset_position
            )
            mock_process_all_trc_tags.return_value = bytearray(
                b"Modified JP2 content"
            )

            # Call the method under test
            result, remediated_bytes = self.reader.remediate_jp2()

            # Assert that initialize_validator was called once
            mock_initialize_validator.assert_called_once()

            # Assert that validator._isValid() was called once
            mock_validator._isValid.assert_called_once()

            # Assert that check_boxes was called once
            mock_check_boxes.assert_called_once()

            # Assert that process_all_trc_tags was called with
            # the correct header_offset_position
            mock_process_all_trc_tags.assert_called_once_with(100)

            # Assert that remediated_bytes contains the modified content
            self.assertEqual(
                remediated_bytes, bytearray(b"Modified JP2 content")
            )

    # Test for process_trc_tag: when trc_tag_size != curv_trc_field_length
    def test_process_trc_tag_size_mismatch(self):
        # Prepare test data where trc_tag_size does
        # not match curv_trc_field_length
        trc_hex = b"\x72\x54\x52\x43"  # Hex for 'rTRC'
        trc_name = "rTRC"
        trc_position = (
            10  # Arbitrary position where trc_hex is found in new_contents
        )

        # Set trc_tag_offset and trc_tag_size with values that
        # will cause a mismatch
        trc_tag_offset = 50  # Arbitrary offset value
        trc_tag_size = (
            20  # Set intentionally different from curv_trc_field_length
        )

        # Build the trc_tag_entry (12 bytes): signature + offset + size
        trc_tag_entry = (
            trc_hex
            + trc_tag_offset.to_bytes(4, "big")
            + trc_tag_size.to_bytes(4, "big")
        )

        # Prepare new_contents with the trc_tag_entry at trc_position
        new_contents = bytearray(
            b"\x00" * trc_position + trc_tag_entry + b"\x00" * 200
        )

        # Set header_offset_position to a valid integer
        header_offset_position = 5  # Arbitrary valid value

        # Prepare curv_profile data with curv_trc_gamma_n
        # such that curv_trc_field_length != trc_tag_size
        curv_trc_gamma_n = 1  # Set gamma_n to 1
        curv_trc_field_length = curv_trc_gamma_n * 2 + 12  # Calculates to 14

        # Build curv_profile (12 bytes): signature + reserved + gamma_n
        curv_signature = b"curv"  # Signature 'curv'
        curv_reserved = (0).to_bytes(4, "big")  # Reserved bytes set to zero
        curv_trc_gamma_n_bytes = curv_trc_gamma_n.to_bytes(4, "big")
        curv_profile = curv_signature + curv_reserved + curv_trc_gamma_n_bytes

        # Calculate curv_trc_position based on
        # trc_tag_offset and header_offset_position
        curv_trc_position = trc_tag_offset + header_offset_position

        # Ensure new_contents is large enough to hold the
        # curv_profile at the calculated position
        required_length = curv_trc_position + len(curv_profile)
        if len(new_contents) < required_length:
            new_contents.extend(
                b"\x00" * (required_length - len(new_contents))
            )

        # Insert curv_profile into new_contents at curv_trc_position
        new_contents[
            curv_trc_position : curv_trc_position + len(curv_profile)  # noqa
        ] = curv_profile

        # Mock the logger to capture warnings
        self.reader.logger = MagicMock()

        # Call the method under test
        result_contents = self.reader.process_trc_tag(
            trc_hex, trc_name, new_contents, header_offset_position
        )

        # Verify that the trc_tag_size in new_contents was
        # updated to curv_trc_field_length
        updated_trc_tag_size_bytes = result_contents[
            trc_position + 8 : trc_position + 12  # noqa
        ]
        updated_trc_tag_size = int.from_bytes(
            updated_trc_tag_size_bytes, "big"
        )
        self.assertEqual(updated_trc_tag_size, curv_trc_field_length)

        # Verify that the appropriate warning was logged
        expected_warning = (
            f"'{trc_name}' Tag Size ({trc_tag_size}) does not "
            f"match 'curv_{trc_name}_field_length' ({curv_trc_field_length}). "
            "Modifying the size..."
        )
        self.reader.logger.warning.assert_any_call(expected_warning)

    # Test for process_trc_tag: when curv_trc_gamma_n != 1, in this case is 2
    def test_process_trc_tag_sets_skip_remediation(self):
        """
        Ensure that if curv_trc_gamma_n != 1, skip_remediation is set to True.
        """
        # Prepare minimal file_contents with a single TRC tag
        self.reader.file_contents = bytearray(
            b"\x00" * 50
            + b"\x72\x54\x52\x43"  # 'rTRC'
            + b"\x00\x00\x00\x64"  # Some offset (100) in big-endian
            + b"\x00\x00\x00\x20"  # Tag size (32) in big-endian
            + b"\x00" * 200  # Just extra space
        )

        # Force a header_offset_position that points to 'curv' data
        header_offset_position = 50

        # Insert a 'curv' signature + reserved + gamma_n != 1 at
        # position (100 + header_offset_position)
        curv_trc_position = 100 + header_offset_position
        curv_data = (
            b"curv" + (0).to_bytes(4, "big") + (2).to_bytes(4, "big")
        )  # gamma_n = 2
        self.reader.file_contents[
            curv_trc_position : curv_trc_position + 12  # noqa
        ] = curv_data

        new_contents = bytearray(self.reader.file_contents)

        # Call the method
        self.reader.process_trc_tag(
            b"\x72\x54\x52\x43", "rTRC", new_contents, header_offset_position
        )

        # Assert skip_remediation is now True
        self.assertTrue(
            self.reader._skip_remediation(),
            "Expected skip_remediation to be True when gamma_n != 1.",
        )

    def test_remediate_jp2_skip_remediation(self):
        """
        Ensure that remediate_jp2 properly handles skip_remediation.
        """
        self.reader.file_contents = b"SomeJP2Content"
        self.reader.curv_trc_gamma_n = 2  # Force skipping

        result, remediated_bytes = self.reader.remediate_jp2()

        # Verify result has skip_remediation set
        self.assertTrue(result.is_skip_remediation())

    # Test to ensure InMemoryBoxReader never calls write_modified_file
    @patch("builtins.open")
    def test_in_memory_never_writes_to_disk(self, mock_open):
        """
        Comprehensive test to ensure InMemoryBoxReader never writes to disk
        during any operation.
        """
        # Call remediate_jp2 multiple times
        for _ in range(3):
            result, remediated_bytes = self.reader.remediate_jp2()

        # Verify open was never called with 'wb' or 'w' mode
        for call in mock_open.call_args_list:
            if len(call[0]) > 1:
                mode = call[0][1]
                self.assertNotIn(
                    "w", mode, "InMemoryBoxReader should never write to disk"
                )

    # Test that file_path is set to ::memory::
    def test_file_path_is_memory(self):
        """
        Ensure that InMemoryBoxReader always has file_path set to ::memory::
        """
        self.assertEqual(self.reader.file_path, "::memory::")


if __name__ == "__main__":
    unittest.main()
