from argparse import ArgumentParser, ArgumentTypeError
from pathlib import Path


def resolve_path(path_str: str) -> Path:
    """
    Expands user tildes and resolves the string to an absolute path.
    Used for output files that might not exist yet.
    """
    return Path(path_str).expanduser().resolve()


def existing_file(path_str: str) -> Path:
    """
    Expands the path and enforces early boundary validation to ensure
    the file actually exists on the disk before the script continues.
    """
    path = resolve_path(path_str)
    if not path.is_file():
        raise ArgumentTypeError(
            f"The file '{path}' does not exist or is not a file.")
    return path


def parse_args():
    """
    Parse command line arguments for the abook_google_merge script.
    Returns a namespace with the parsed arguments.
    """
    arg_parser = ArgumentParser(
        prog='abook_google_merge',
        description='Update abook addressbook with missing entries'
                    'from a google contacts csv file.'
    )
    arg_parser.add_argument(
        '-i', '--input', type=existing_file, default='~/.abook/addressbook',
        help='Path to the abook file (default: ~/.abook/addressbook)'
    )
    arg_parser.add_argument(
        '-g', '--google', type=existing_file, default='google.csv',
        help='Path to the google contacts csv file (default: google.csv)'
    )
    arg_parser.add_argument(
        '-o', '--output', type=resolve_path, default=None,
        help='Path to the output abook file (default: overwrite input file)'
    )
    arg_parser.add_argument(
        '-p', '--partially-matched', type=str.lower,
        choices=['u', 'update', 'a', 'add', 's', 'skip'], default=None,
        help='Action for partially matched entries instead of asking; '
             '"update" still asks which entry if several match (default: ask)'
    )
    arg_parser.add_argument(
        '-u', '--unmatched', type=str.lower,
        choices=['a', 'add', 's', 'skip'], default=None,
        help='Action for unmatched entries instead of asking (default: ask)'
    )
    args = arg_parser.parse_args()
    if args.output is None:
        args.output = args.input
    # Reduce long action names to their initial letter
    if args.partially_matched:
        args.partially_matched = args.partially_matched[0]
    if args.unmatched:
        args.unmatched = args.unmatched[0]
    return args
