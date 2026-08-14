# Update abook addressbook with missing entries from a google contacts csv file

import csv
from enum import Enum
import os
import shutil


class AbookEntry:
    """
    A single entry in the abook addressbook.
    Stores all fields as key-value pairs in a dictionary, along with
    normalized values for name, email, and phone for matching purposes
    """
    email_fields = ['email']
    phone_fields = ['phone', 'mobile', 'workphone']
    list_fields = email_fields + phone_fields

    google_name_parts = [
        'Name Prefix', 'First Name', 'Middle Name', 'Last Name', 'Name Suffix'
    ]

    class MatchType(Enum):
        """
        Enum for match types when comparing entries.
        """
        UNMATCHED = 0
        PARTIAL_MATCH = 1
        FULL_MATCH = 2

    def __init__(self, fields):
        """
        Initialize an AbookEntry with the given fields.
        Calculate normalized values for name, email, and phone
        """
        self.fields = fields
        self._normalized_name = AbookEntry.normalize_name(
            self.fields.setdefault('name', '')
        )
        self._normalized_emails = set([
            AbookEntry.normalize_email(email)
            for email_field in AbookEntry.email_fields
            for email in self.fields.setdefault(email_field, [])
        ])
        self._normalized_phones = set([
            AbookEntry.normalize_phone(phone)
            for phone_field in AbookEntry.phone_fields
            for phone in self.fields.setdefault(phone_field, [])
        ])

    @classmethod
    def from_google_entry(cls, google_entry):
        """
        Create an AbookEntry from a google contacts entry.
        Keep a few relevant fields: name, email, phone, mobile, workphone
        """
        abook_entry = {}

        # Merge the name-related fields into a single 'name' field
        abook_entry['name'] = ' '.join(
            google_entry.get(part, '') for part in cls.google_name_parts
            if google_entry.get(part)
        ).strip()

        # Combine the email fields into a single 'email' field
        abook_entry['email'] = sum(
            (
                v.split(',') for k, v in google_entry.items()
                if 'E-mail' in k and 'Value' in k and v
            ), start=[]
        )

        # Phone labels need to be combined in a smarter way
        # If "Phone - Label N" is "Mobile" then map to "mobile" in abook
        # "Work" -> "workphone", anything else to "phone"
        phone_labels = {
            'Mobile': 'mobile',
            'Work': 'workphone'
        }
        for k, v in google_entry.items():
            if 'Phone' in k and 'Value' in k and v:
                label_key = k.replace('Value', 'Label')
                label = google_entry.get(label_key, '')
                abook_key = phone_labels.get(label, 'phone')
                abook_entry.setdefault(abook_key, []).extend(v.split(','))
        return cls(abook_entry)

    @staticmethod
    def normalize_name(name):
        return name.replace('.', '').lower()

    @staticmethod
    def normalize_email(email):
        return email.lower()

    @staticmethod
    def normalize_phone(phone):
        return ''.join(filter(str.isdigit, phone))

    def add_email(self, email: str):
        """
        Safely append a new email, updating both the raw list and the set.
        """
        self.fields['email'].append(email)
        self._normalized_emails.add(AbookEntry.normalize_email(email))

    def add_phone(self, phone: str, label: str):
        """
        Safely append a new phone number to a specific label,
        updating both the raw list and the set.
        """
        self.fields[label].append(phone)
        self._normalized_phones.add(AbookEntry.normalize_phone(phone))

    def __str__(self):
        """
        Return a string representation of the entry for debugging.
        """
        return f"{self.fields}"

    def to_abook_entry_string(self, header):
        """
        Convert entry to the abook addressbook format string, with header id.
        """
        lines = [f'[{header}]']
        for key, value in self.fields.items():
            if value:
                if isinstance(value, list):
                    value = ','.join(value)
                lines.append(f'{key}={value}')
        return '\n'.join(lines) + '\n\n'

    def get_normalized_fields(self):
        """
        Return a dictionary of normalized fields for matching purposes.
        """
        return (
            self._normalized_name,
            self._normalized_emails, self._normalized_phones
        )

    def update_entry(self, other_entry):
        """
        Update the current entry with information from another entry.
        Change name (unless empty) only with user permission
        Only adds new emails and phone numbers, does not remove existing ones.
        """
        if other_entry._normalized_name:
            change_name = False
            if not self._normalized_name:
                change_name = True
            elif other_entry._normalized_name != self._normalized_name:
                # Ask the user if they want to update the name
                print(
                    "Do you want to update the name "
                    f"from '{self.fields['name']}' "
                    f"to '{other_entry.fields['name']}'? (y/n)"
                )
                user_input = input().strip().lower()
                if user_input == 'y':
                    change_name = True
            if change_name:
                self.fields['name'] = other_entry.fields['name']
                self._normalized_name = other_entry._normalized_name

        for group, group_set, group_normalizer in zip(
            [AbookEntry.email_fields, AbookEntry.phone_fields],
            [self._normalized_emails, self._normalized_phones],
            [AbookEntry.normalize_email, AbookEntry.normalize_phone]
        ):
            for key in group:
                # Do not change original order, only append new values
                # Do not add item that exists even in a different field
                for value in other_entry.fields.get(key, []):
                    normalized_value = group_normalizer(value)
                    if normalized_value not in group_set:
                        self.fields.setdefault(key, []).append(value)
                        group_set.add(normalized_value)


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
