import csv
from src.abookentry import AbookEntry


class Abook:
    """An abook addressbook."""

    def __init__(self, entries=None, format_entry=None):
        self.entries = entries if entries is not None else []
        self.format_entry = format_entry

    @classmethod
    def from_abook_file(cls, file_path):
        """Read the abook addressbook and populate entries."""
        with open(file_path, 'r') as f:
            lines = f.readlines()

        entries = []
        current_entry = {}
        format_entry = None
        is_format = False
        for line in map(str.strip, lines):
            # Ignore comments and empty lines
            if not line or line.startswith('#'):
                continue

            if line.startswith('[') and line.endswith(']'):
                # New entry starts, save the current entry if it exists
                if current_entry:
                    if is_format:
                        format_entry = current_entry
                    else:
                        entries.append(AbookEntry(current_entry))
                    current_entry = {}
                is_format = line == '[format]'
            elif '=' in line:
                key, value = [x.strip() for x in line.split('=', 1)]
                if key in AbookEntry.list_fields:
                    value = value.split(',')
                current_entry[key] = value
        if current_entry:
            if is_format:
                format_entry = current_entry
            else:
                entries.append(AbookEntry(current_entry))

        return cls(entries=entries, format_entry=format_entry)

    @classmethod
    def from_google_file(cls, file_path):
        """Read the google contacts csv file and convert to abook."""
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Select only non-empty fields while converting to dict list
            entries = [
                {k: ','.join(v.split(' ::: ')) for k, v in row.items() if v}
                for row in reader
            ]
        abook_entries = list(map(AbookEntry.from_google_entry, entries))

        return cls(entries=abook_entries)

    def format_string(self):
        """Create a string representation of the format entry."""
        return AbookEntry._to_abook_entry_string(self.format_entry, 'format')

    def write_to_file(self, file_path):
        """Write the abook entries to a file in the abook format."""
        with open(file_path, 'w') as f:
            if self.format_entry:
                f.write(self.format_string())
            for i, entry in enumerate(self.entries):
                f.write(entry.to_abook_entry_string(i))

    def find_matching_abook_entries(self, other_entry):
        """Find matching abook entries for an entry from another abook."""
        matching_entries = []

        for entry in self.entries:
            match = entry.get_match(other_entry)
            if match == AbookEntry.MatchType.FULL_MATCH:
                return AbookEntry.MatchType.FULL_MATCH, entry
            elif match == AbookEntry.MatchType.PARTIAL_MATCH:
                matching_entries.append(entry)

        if matching_entries:
            return AbookEntry.MatchType.PARTIAL_MATCH, matching_entries
        else:
            return AbookEntry.MatchType.UNMATCHED, None

    def update_entries(
        self, other_abook, partial_action=None, unmatched_action=None
    ):
        """
        Update abook entries with information from another abook.
        partial_action ('u'/'a'/'s') and unmatched_action ('a'/'s') answer
        the respective questions automatically; None means ask the user.
        'u' with several matching entries still asks which one to update.
        """
        for other_entry in other_abook.entries:
            if not other_entry.fields.get('name') or not any(
                other_entry.fields.get(field)
                for field in AbookEntry.list_fields
            ):
                continue
            match_type, matching_entries = self.find_matching_abook_entries(
                other_entry
            )

            if match_type == AbookEntry.MatchType.UNMATCHED:
                print(f"Unmatched entry: {other_entry}")
                if unmatched_action:
                    add_entry = unmatched_action == 'a'
                else:
                    print("Do you want to add this entry to abook? (y/n)")
                    add_entry = input().strip().lower() == 'y'
                if add_entry:
                    self.entries.append(other_entry)
                    print("Entry added.")
                else:
                    print("Entry not added.")
            elif match_type == AbookEntry.MatchType.PARTIAL_MATCH:
                print(f"Partial match found for entry: {other_entry}")
                print("Matching entries:")
                for i, entry in enumerate(matching_entries):
                    print(f"{i + 1}: {entry}")
                if partial_action:
                    user_input = partial_action
                else:
                    print(
                        "Do you want to update an existing entry"
                        " or add a new one? (u/a/n)"
                    )
                    user_input = input().strip().lower()
                if user_input == 'u':
                    if len(matching_entries) == 1:
                        entry_to_update = matching_entries[0]
                    else:
                        print("Select the entry number to update:")
                        entry_number = int(input().strip()) - 1
                        if 0 <= entry_number < len(matching_entries):
                            entry_to_update = matching_entries[entry_number]
                        else:
                            print("Invalid entry number. Skipping update.")
                            continue
                    entry_to_update.update_entry(other_entry)
                    print("Entry updated.")
                elif user_input == 'a':
                    self.entries.append(other_entry)
                    print("Entry added.")
