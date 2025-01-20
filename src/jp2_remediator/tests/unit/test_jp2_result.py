from jp2_remediator.jp2_result import Jp2Result


class TestJp2Result:

    def test_result_code_empty(self):
        result = Jp2Result("test.jp2")
        assert result.result_code() == 1

    def test_result_code_valid(self):
        result = Jp2Result("test.jp2")
        result.set_modified_file_path("test_modified.jp2")
        result.set_validity(True)
        assert result.result_code() == 4

    def test_result_code_invalid(self):
        result = Jp2Result("test.jp2")
        result.set_validity(False)
        assert result.result_code() == 2

    def test_result_code_skip_remediation(self):
        result = Jp2Result("test.jp2")
        result.set_validity(True)
        result.set_skip_remediation(2)
        assert result.result_code() == 3

    def test_result_code_neutral(self):
        result = Jp2Result("test.jp2")
        result.set_validity(True)
        assert result.result_code() == 0

    def test_repr(self):
        result = Jp2Result("test.jp2")
        assert repr(result) == "Jp2Result(path=test.jp2, "\
            "is_empty=True, "\
            "is_valid=False, "\
            "curv_trc_gamma_n=None, "\
            "modified_file_path=None)"
