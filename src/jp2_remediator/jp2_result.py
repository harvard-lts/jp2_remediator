class Jp2Result:
    """
    Represents the result of processing a JP2 file.
    - path: The path to the JP2 file.
    - is_empty: True if the JP2 file is empty, False otherwise.
    - is_valid: True if the JP2 file is valid per Jpylyzer, False otherwise.
    - curv_trc_gamma_n: The value of the curv, trc, or gamma box n parameter.
    - modified_file_path: The path to the modified JP2 file.

    The result_code method returns an integer code based on the result:
    - -1: Neutral, no modifications needed
    - 0: Success
    - 1: Failure, empty JP2 file
    - 2: Failure, invalid JP2 file
    - 3: Failure, skipped remediation, unexpected curv_trc_gamma_n
    """

    def __init__(self, path):
        self.path = path
        self.is_empty = True
        self.is_valid = False
        self.curv_trc_gamma_n = None
        self.modified_file_path = None
        self.curv_trc_gamma_n = None

    def empty_result(self):
        self.is_empty = True
        return self

    def set_validity(self, is_valid):
        self.is_empty = False
        self.is_valid = is_valid

    def set_skip_remediation(self, curv_trc_gamma_n):
        self.is_empty = False
        self.curv_trc_gamma_n = curv_trc_gamma_n

    def is_skip_remediation(self):
        return self.curv_trc_gamma_n is not None and self.curv_trc_gamma_n != 1

    def set_modified_file_path(self, modified_file_path):
        self.modified_file_path = modified_file_path

    def get_modified_file_path(self):
        return self.modified_file_path

    def result_code(self):
        if self.is_empty:
            return 1  # failure, empty jp2
        elif not self.is_valid:
            return 2  # failure, invalid jp2
        elif self.is_skip_remediation():
            return 3  # failure, skipped remediation, unexpected curv_trc_gamma_n
        elif self.modified_file_path is None:
            return 0  # neutral, no modifications needed

        return 4  # successful remediation

    def __repr__(self):
        return f"Jp2Result(path={self.path}, "\
            f"is_empty={self.is_empty}, "\
            f"is_valid={self.is_valid}, "\
            f"curv_trc_gamma_n={self.curv_trc_gamma_n}, "\
            f"modified_file_path={self.modified_file_path})"
