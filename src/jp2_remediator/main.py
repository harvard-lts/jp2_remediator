import argparse
from jp2_remediator.box_reader_factory import BoxReaderFactory
from jp2_remediator.processor import Processor


def main():
    """Main entry point for the JP2 file processor."""
    processor = Processor(BoxReaderFactory())

    parser = argparse.ArgumentParser(description="JP2 file processor")

    # Create mutually exclusive subparsers for specifying input source
    subparsers = parser.add_subparsers(
        title="Input source", dest="input_source"
    )

    # Subparser for processing a single JP2 file
    file_parser = subparsers.add_parser(
        "file", help="Process a single JP2 file"
    )
    file_parser.add_argument(
        "file", help="Path to a single JP2 file to process"
    )
    file_parser.set_defaults(
        func=lambda args: processor.process_file(args.file)
    )

    # Subparser for processing all JP2 files in a directory
    directory_parser = subparsers.add_parser(
        "directory", help="Process all JP2 files in a directory"
    )
    directory_parser.add_argument(
        "directory", help="Path to a directory of JP2 files to process"
    )
    directory_parser.set_defaults(
        func=lambda args: processor.process_directory(args.directory)
    )

    # Subparser for processing a single JP2 file in S3
    s3_file_parser = subparsers.add_parser(
        "s3-file", help="Process a single JP2 file in S3"
    )
    s3_file_parser.add_argument(
        "--input-bucket",
        help="Name of the AWS S3 bucket containing the JP2 file",
        required=True,
    )
    s3_file_parser.add_argument(
        "--input-key",
        help="Key (path) of the JP2 file in the S3 bucket",
        required=True,
    )
    s3_file_parser.add_argument(
        "--output-bucket",
        help="Name of the AWS S3 bucket to upload the modified file (optional)",  # noqa E501
        required=True,
    )
    s3_file_parser.add_argument(
        "--output-key",
        help="Full key (path) for the uploaded file",
        required=True,
    )
    s3_file_parser.set_defaults(
        func=lambda args: processor.process_s3_file(
            args.input_bucket,
            args.input_key,
            args.output_bucket,
            args.output_key,
        )
    )

    args = parser.parse_args()

    if hasattr(args, "func"):
        # Returns Jp2Result object
        result = args.func(args)
        print(result)
        return result
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
