import datetime
from jp2_remediator import configure_logger
from jpylyzer import boxvalidator

from jp2_remediator.jp2_result import Jp2Result


class BoxReader:
    def __init__(self, file_path):
        # Initializes BoxReader with a file path.
        self.file_path = file_path
        self.file_contents = self.read_file(file_path)
        self.validator = None
        self.curv_trc_gamma_n = None
        self.logger = configure_logger(__name__)

    def read_file(self, file_path):
        # Reads the file content from the given path.
        try:
            with open(file_path, "rb") as file:
                return file.read()
        except IOError as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None

    def initialize_validator(self):
        # Initializes the jpylyzer BoxValidator for JP2 file validation.
        options = {
            "validationFormat": "jp2",
            "verboseFlag": True,
            "nullxmlFlag": False,
            "packetmarkersFlag": False,
        }
        self.validator = boxvalidator.BoxValidator(
            options, "JP2", self.file_contents
        )
        self.validator.validate()
        return self.validator

    def find_box_position(self, box_hex):
        # Finds the position of the specified box in the file.
        return self.file_contents.find(box_hex)

    def check_boxes(self):
        # Checks for presence of 'jp2h' and 'colr' boxes in file contents.
        jp2h_position = self.find_box_position(
            b"\x6a\x70\x32\x68"
        )  # search hex for 'jp2h'
        if jp2h_position != -1:
            self.logger.debug(
                f"'jp2h' found at byte position: {jp2h_position}"
            )
        else:
            self.logger.debug("'jp2h' not found in the file.")

        colr_position = self.find_box_position(
            b"\x63\x6f\x6c\x72"
        )  # search hex for 'colr'
        if colr_position != -1:
            self.logger.debug(
                f"'colr' found at byte position: {colr_position}"
            )
        else:
            self.logger.debug("'colr' not found in the file.")

        header_offset_position = self.process_colr_box(colr_position)

        return header_offset_position

    def process_colr_box(self, colr_position):
        # Processes the 'colr' box to determine header offset position.
        if colr_position != -1:
            self.logger.debug(
                f"'colr' found at byte position: {colr_position}"
            )
            meth_byte_position = colr_position + 4
            # ISO/IEC 15444-1:2019(E) Figure I.10 colr specification box
            # byte position of METH value after 'colr'
            meth_value = self.file_contents[meth_byte_position]
            self.logger.debug(
                f"'meth' value: {meth_value} at byte position: "
                f"{meth_byte_position}"
            )

            if meth_value == 1:
                header_offset_position = meth_byte_position + 7
                # ISO/IEC 15444-1:2019(E) Table I.11 colr specification box,
                # if meth is 1 then color profile starts at byte position 7
                # after 'colr'
                self.logger.debug(
                    f"'meth' is 1, setting header_offset_position to: "
                    f"{header_offset_position}"
                )
            elif meth_value == 2:
                header_offset_position = meth_byte_position + 3
                # ISO/IEC 15444-1:2019(E) Table I.11 colr specification box,
                # if meth is 2 then color profile (ICC profile) starts at byte
                # position 3 after 'colr'
                self.logger.debug(
                    "'meth' is 2, setting header_offset_position to: "
                    f"{header_offset_position} (start of ICC profile)"
                )
            else:
                self.logger.debug(
                    f"'meth' value {meth_value} is not recognized "
                    "(must be 1 or 2)."
                )
                header_offset_position = None
        else:
            self.logger.debug("'colr' not found in the file.")
            header_offset_position = None

        return header_offset_position

    def process_trc_tag(
        self, trc_hex, trc_name, new_contents, header_offset_position
    ):
        # Processes the TRC tag and modifies contents if necessary.
        trc_position = new_contents.find(trc_hex)
        if trc_position == -1:
            self.logger.debug(f"'{trc_name}' not found in the file.")
            return new_contents

        self.logger.debug(
            f"'{trc_name}' found at byte position: {trc_position}"
        )
        trc_tag_entry = new_contents[trc_position : trc_position + 12]  # noqa
        # 12-byte tag entry length

        if len(trc_tag_entry) != 12:
            self.logger.debug(
                f"Could not extract the full 12-byte '{trc_name}' tag entry."
            )
            return new_contents

        trc_tag_signature = trc_tag_entry[0:4]
        # ICC.1:2022 Table 24 tag signature, e.g. 'rTRC'
        trc_tag_offset = int.from_bytes(trc_tag_entry[4:8], byteorder="big")
        # ICC.1:2022 Table 24 tag offset
        trc_tag_size = int.from_bytes(trc_tag_entry[8:12], byteorder="big")
        # ICC.1:2022 Table 24 tag size
        self.logger.debug(f"'{trc_name}' Tag Signature: {trc_tag_signature}")
        self.logger.debug(f"'{trc_name}' Tag Offset: {trc_tag_offset}")
        self.logger.debug(f"'{trc_name}' Tag Size: {trc_tag_size}")

        if header_offset_position is None:
            self.logger.debug(
                f"Cannot calculate 'curv_{trc_name}_position' "
                "due to an unrecognized 'meth' value."
            )
            return new_contents

        curv_trc_position = (
            trc_tag_offset + header_offset_position
        )  # start of curv profile data
        curv_profile = new_contents[
            curv_trc_position : curv_trc_position + 12  # noqa
        ]  # 12-byte curv profile data length

        if len(curv_profile) < 12:
            self.logger.debug(
                f"Could not read the full 'curv' profile data for {trc_name}."
            )
            return new_contents

        curv_signature = curv_profile[0:4].decode(
            "utf-8"
        )  # ICC.1:2022 Table 35 tag signature
        curv_reserved = int.from_bytes(
            curv_profile[4:8], byteorder="big"
        )  # ICC.1:2022 Table 35 reserved 0's
        curv_trc_gamma_n = int.from_bytes(
            curv_profile[8:12], byteorder="big"
        )  # ICC.1:2022 Table 35 n value

        self.logger.debug(
            f"'curv' Profile Signature for {trc_name}: {curv_signature}"
        )
        self.logger.debug(f"'curv' Reserved Value: {curv_reserved}")
        self.logger.debug(
            f"'curv_{trc_name}_gamma_n' Value: {curv_trc_gamma_n}"
        )
        curv_trc_field_length = (
            curv_trc_gamma_n * 2 + 12
        )  # ICC.1:2022 Table 35 2n field length
        self.logger.debug(
            f"'curv_{trc_name}_field_length': {curv_trc_field_length}"
        )

        # If 'curv_trc_gamma_n' is not 1, set skip_remediation = True
        # and skip further remediation.
        self.curv_trc_gamma_n = curv_trc_gamma_n
        if curv_trc_gamma_n != 1:
            self.logger.warning(
                f"Warning: In file '{self.file_path}', "
                f"'curv_{trc_name}_gamma_n' value is {curv_trc_gamma_n}, "
                "expected 1. Remediation will be skipped for this file."
            )
            return new_contents

        if trc_tag_size != curv_trc_field_length:
            self.logger.warning(
                f"'{trc_name}' Tag Size ({trc_tag_size}) "
                f"does not match 'curv_{trc_name}_field_length' "
                f"({curv_trc_field_length}). Modifying the size..."
            )
            new_trc_size_bytes = curv_trc_field_length.to_bytes(
                4, byteorder="big"
            )
            new_contents[trc_position + 8 : trc_position + 12] = (  # noqa
                new_trc_size_bytes
            )
        return new_contents

    def process_all_trc_tags(self, header_offset_position):
        # Function to process 'TRC' tags (rTRC, gTRC, bTRC).
        new_file_contents = bytearray(self.file_contents)
        trc_tags = {
            b"\x72\x54\x52\x43": "rTRC",  # search hex for 'rTRC'
            b"\x67\x54\x52\x43": "gTRC",  # search hex for 'gTRC'
            b"\x62\x54\x52\x43": "bTRC",  # search hex for 'bTRC'
        }

        for trc_hex, trc_name in trc_tags.items():
            new_file_contents = self.process_trc_tag(
                trc_hex, trc_name, new_file_contents, header_offset_position
            )

        return new_file_contents

    def write_modified_file(self, new_file_contents):
        # Writes modified file contents to new file if changes were made.
        # Returns the new file path or None if no changes were made.
        if new_file_contents != self.file_contents:
            timestamp = datetime.datetime.now().strftime(
                "%Y%m%d"
            )  # use "%Y%m%d_%H%M%S" for more precision
            new_file_path = self.file_path.replace(
                ".jp2", f"_modified_{timestamp}.jp2"
            )
            with open(new_file_path, "wb") as new_file:
                new_file.write(new_file_contents)
            self.logger.info(
                f"New JP2 file created with modifications: {new_file_path}"
            )
            return new_file_path
        else:
            self.logger.info(
                "No modifications needed. No new file created: "
                f"{self.file_path}"
            )
            return None

    def read_jp2_file(self):
        # Main function to read, validate, and check to remediate JP2 files.
        # Returns result object with the modified file_path and remediation
        # status
        result = Jp2Result(self.file_path)
        if not self.file_contents:
            return result.empty_result()

        self.initialize_validator()
        is_valid = self.validator._isValid()
        self.logger.info(f"Is file valid? {is_valid}")
        result.set_validity(is_valid)

        header_offset_position = self.check_boxes()
        new_file_contents = self.process_all_trc_tags(header_offset_position)

        # If any TRC had a curv_trc_gamma_n != 1,
        # skip writing the modified file.
        result.set_skip_remediation(self.curv_trc_gamma_n)
        if not self._skip_remediation():
            modified_path = self.write_modified_file(new_file_contents)
            result.set_modified_file_path(modified_path)

        return result

    def _skip_remediation(self):
        skip = self.curv_trc_gamma_n != 1
        if skip:
            self.logger.info(
                "Skip remediation because gamma_n != 1 "
                "for at least one TRC channel."
            )
        return skip
