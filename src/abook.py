import csv
from src.abookentry import AbookEntry


class Abook:
    """A class to represent an abook addressbook."""

    def __init__(self, entries=None, format_entry=None):
        self.entries = entries if entries is not None else []
        self.format_entry = format_entry

    @classmethod
    def from_abook_file(cls, file_path):
        """Read the abook addressbook file and populate entries."""
        with open(file_path, 'r') as f:
            # Add a dummy line to ensure the last entry is processed
            lines = f.readlines() + ['[dummy]']

        entries = []
        current_entry = {}
        format_entry = None
        is_format = False
        for line in lines:
            line = line.strip()

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
        abook_entries = [
            AbookEntry.from_google_entry(entry) for entry in entries
        ]

        return cls(entries=abook_entries)

    def format_string(self):
        """Create a string representation of the format entry."""
        return AbookEntry._to_abook_entry_string(self.format_entry, 'format')

    def write_to_file(self, file_path):
        """Convert a list of dictionaries to an abook addressbook file."""
        with open(file_path, 'w') as f:
            if self.format_entry:
                f.write(self.format_string())
            for i, entry in enumerate(self.entries):
                f.write(entry.to_abook_entry_string(i))

    def find_matching_abook_entries(self, google_entry):
        """Find a matching abook entry for a given google entry."""
        (
            google_name, google_emails, google_phones
        ) = google_entry.get_normalized_fields()
        matching_entries = []

        for entry in self.entries:
            name, emails, phones = entry.get_normalized_fields()
            name_match = google_name and name and google_name == name
            email_match_count = len(google_emails.intersection(emails))
            phone_match_count = len(google_phones.intersection(phones))

            if (
                name_match and email_match_count == len(google_emails) and
                phone_match_count == len(google_phones)
            ):
                return AbookEntry.MatchType.FULL_MATCH, entry
            elif name_match or email_match_count > 0 or phone_match_count > 0:
                matching_entries.append(entry)

        if matching_entries:
            return AbookEntry.MatchType.PARTIAL_MATCH, matching_entries
        else:
            return AbookEntry.MatchType.UNMATCHED, None

    def update_entries(self, other_abook):
        """Update abook entries with information from google entries."""
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
                print("Do you want to add this entry to abook? (y/n)")
                user_input = input().strip().lower()
                if user_input == 'y':
                    self.entries.append(other_entry)
                    print("Entry added.")
                else:
                    print("Entry not added.")
            elif match_type == AbookEntry.MatchType.PARTIAL_MATCH:
                print(f"Partial match found for entry: {other_entry}")
                print("Matching entries:")
                for i, entry in enumerate(matching_entries):
                    print(f"{i + 1}: {entry}")
                print(
                    "Do you want to update an existing entry or add a new one?"
                    " (u/a/n)"
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
