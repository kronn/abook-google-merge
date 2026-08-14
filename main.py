# Update abook addressbook with missing entries from a google contacts csv file

import csv
import os
import shutil


def read_abook_to_entrylist(file_path):
    """Convert the abook addressbook file to a list of dictionaries."""
    # Check if the file exists and raise an exception if it does not
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

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

    return format_entry, entries


def read_google_contacts_to_dictlist(file_path):
    """Convert the google contacts csv file to a list of dictionaries."""

    # Check if the file exists and raise an exception if it does not
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        # Select only non-empty fields while converting to dict list
        entries = [
            {k: ','.join(v.split(' ::: ')) for k, v in row.items() if v}
            for row in reader
        ]

    return entries


def to_abook_format_string(format_entry):
    """Create a string representation of the abook format entry."""
    lines = ['[format]']
    for key, value in format_entry.items():
        if value:
            if isinstance(value, list):
                value = ','.join(value)
            lines.append(f'{key}={value}')
    return '\n'.join(lines) + '\n\n'


def write_dictlist_to_abook(file_path, format_entry, entries):
    """Convert a list of dictionaries to an abook addressbook file."""
    with open(file_path, 'w') as f:
        if format_entry:
            f.write(to_abook_format_string(format_entry))
        for i, entry in enumerate(entries):
            f.write(entry.to_abook_entry_string(i))


def find_matching_abook_entries(google_entry, abook_entries):
    """Find a matching abook entry for a given google entry."""
    (
        google_name, google_emails, google_phones
    ) = google_entry.get_normalized_fields()
    matching_entries = []

    for abook_entry in abook_entries:
        (
            abook_name, abook_emails, abook_phones
        ) = abook_entry.get_normalized_fields()
        name_match = google_name and abook_name and google_name == abook_name
        email_match_count = len(google_emails.intersection(abook_emails))
        phone_match_count = len(google_phones.intersection(abook_phones))

        if (
            name_match and email_match_count == len(google_emails) and
            phone_match_count == len(google_phones)
        ):
            return AbookEntry.MatchType.FULL_MATCH, abook_entry
        elif name_match or email_match_count > 0 or phone_match_count > 0:
            matching_entries.append(abook_entry)

    if matching_entries:
        return AbookEntry.MatchType.PARTIAL_MATCH, matching_entries
    else:
        return AbookEntry.MatchType.UNMATCHED, None


def update_abook_entries(abook_entries, google_entries):
    """Update abook entries with information from google entries."""
    for google_entry in google_entries:
        if not google_entry.fields.get('name') or not any(
            google_entry.fields.get(field) for field in AbookEntry.list_fields
        ):
            continue
        match_type, matching_entries = find_matching_abook_entries(
            google_entry, abook_entries
        )

        if match_type == AbookEntry.MatchType.UNMATCHED:
            print(f"Unmatched entry: {google_entry}")
            print("Do you want to add this entry to abook? (y/n)")
            user_input = input().strip().lower()
            if user_input == 'y':
                abook_entries.append(google_entry)
                print("Entry added.")
            else:
                print("Entry not added.")
        elif match_type == AbookEntry.MatchType.PARTIAL_MATCH:
            print(f"Partial match found for entry: {google_entry}")
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
                    entry_number = int(input().strip())
                    if 1 <= entry_number <= len(matching_entries):
                        entry_to_update = matching_entries[entry_number - 1]
                    else:
                        print("Invalid entry number. Skipping update.")
                        continue
                entry_to_update.update_entry(google_entry)
                print("Entry updated.")
            elif user_input == 'a':
                abook_entries.append(google_entry)
                print("Entry added.")


if __name__ == "__main__":
    # Read the abook addressbook file
    abook_file_path = os.path.expanduser("~/.abook/addressbook")
    format_entry, abook_entries = read_abook_to_entrylist(abook_file_path)
    print(f"Read {len(abook_entries)} entries from abook addressbook.")

    # Read the google contacts csv file and convert to simplified abook format
    google_contacts_file_path = os.path.expanduser("/tmp/contacts.csv")
    google_entries = read_google_contacts_to_dictlist(
        google_contacts_file_path
    )
    google_abook_entries = [
        AbookEntry.from_google_entry(entry) for entry in google_entries
    ]
    print(f"Read {len(google_abook_entries)} entries from google contacts.")

    # Update the abook entries with information from the google contacts
    update_abook_entries(abook_entries, google_abook_entries)

    # Write the updated abook entries back to the addressbook file
    # First create a backup of the original addressbook file
    # Use cp to backup + overwrite original to deal with symlinks
    backup_file_path = abook_file_path + ".bak"
    shutil.copy(abook_file_path, backup_file_path)
    write_dictlist_to_abook(abook_file_path, format_entry, abook_entries)
