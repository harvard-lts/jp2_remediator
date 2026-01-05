from jp2_remediator import configure_logger

from jp2_remediator.box_reader import BoxReader
from jp2_remediator.jp2_result import Jp2Result


class InMemoryBoxReader(BoxReader):
    """
    A box reader that reads image date from a bytearray instead of
    from a file. This class is intended for other apps that use
    jp2_remediator as a library and want to process images in memory.
    This class is not currently used by (or useful to) to command-line
    app.
    """

    def __init__(self, image_bytes: bytes):
        """
        Creates a new box reader that reads bytes from memory instead
        of reading from disk or S3.

        :param self: Description
        :param image_bytes: Description
        :type image_bytes: bytes
        """
        self.file_path = "::memory::"
        self.file_contents = image_bytes
        self.validator = None
        self.curv_trc_gamma_n = None
        self.logger = configure_logger(__name__)

    def remediate_jp2(self) -> tuple[Jp2Result, bytearray]:
        """
        Remediates the contents of the jp2 file in memory and
        returns a Jp2Result describing what work was done. Unlike
        the BoxReader parent class, this writes nothing to disk.

        :param self: Description
        :returns: A Jp2Result describing what work was done, and
            a bytearray containing the bytes of the remediated image.
        """
        # Main function to read, validate, and check to remediate JP2 files.
        # Returns result object with the modified file_path and remediation
        # status
        result = Jp2Result(self.file_path)
        if not self.file_contents:
            return result.empty_result(), self.file_contents

        self.initialize_validator()
        is_valid = self.validator._isValid()
        self.logger.info(f"Is file valid? {is_valid}")
        result.set_validity(is_valid)

        header_offset_position = self.check_boxes()

        # Note that because file_content (bytes) is immutable,
        # the call below copies the bytes into a bytearray, which
        # is mutable, updates the bytearray as necessary, and then
        # returns it.
        remediated_contents = self.process_all_trc_tags(header_offset_position)

        # If any TRC had a curv_trc_gamma_n != 1,
        # skip writing the modified file.
        result.set_skip_remediation(self.curv_trc_gamma_n)

        return result, remediated_contents
