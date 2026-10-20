# Update abook addressbook with missing entries from a google contacts csv file

import shutil
from src.abook import Abook
from src.args import parse_args

if __name__ == "__main__":
    args = parse_args()

    # Read the abook addressbook file
    abook = Abook.from_abook_file(args.input)
    print(f"Read {len(abook.entries)} entries from abook addressbook.")

    # Read the google contacts csv file and convert to simplified abook format
    google = Abook.from_google_file(args.google)
    print(f"Read {len(google.entries)} entries from google contacts.")

    # Update the abook entries with information from the google contacts
    abook.update_entries(
        google,
        partial_action=args.partially_matched,
        unmatched_action=args.unmatched
    )

    # Write the updated abook entries to the output file
    if args.output == args.input:
        # First create a backup of the original addressbook file
        # Use cp to backup + overwrite original to deal with symlinks
        shutil.copy(args.input, args.input.with_suffix('.bak'))
    abook.write_to_file(args.output)
