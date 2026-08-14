# Update abook addressbook with missing entries from a google contacts csv file

import csv
from enum import Enum
import os
import shutil


class MatchType(Enum):
    UNMATCHED = 0
    PARTIAL_MATCH = 1
    FULL_MATCH = 2


phone_fields = ['phone', 'mobile', 'workphone']
email_phone_fields = ['email', *phone_fields]


def read_abook_to_dictlist(file_path):
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
                    entries.append(current_entry)
                current_entry = {}
            is_format = line == '[format]'
        elif '=' in line:
            key, value = [x.strip() for x in line.split('=', 1)]
            if key in email_phone_fields:
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


def convert_google_entry_to_abook_entry(google_entry):
    """Convert a google contacts entry to an abook entry.
    We only keep a few relevant fields: name, email, phone, mobile, workphone
    """
    abook_entry = {}

    # Merge the name-related fields into a single 'name' field
    name_parts = [
        'Name Prefix', 'First Name', 'Middle Name', 'Last Name', 'Name Suffix'
    ]
    abook_entry['name'] = ' '.join(
        google_entry.get(part, '') for part in name_parts
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
            if abook_key in abook_entry:
                abook_entry[abook_key] += v.split(',')
            else:
                abook_entry[abook_key] = v.split(',')
    return abook_entry


def normalize_name(name):
    return name.replace('.', '').lower()


def normalize_email(email):
    return email.lower()


def normalize_phone(phone):
    return ''.join(filter(str.isdigit, phone))


def get_normalized_values(abook_entry):
    """Get normalized values for name, email, and phone from an abook entry."""
    # An entry is considered matching if the name/email/phone number matches
    # under the following rules:
    # Name: remove dots and turn to lower case
    # Email: turn to lower case
    # Phone: remove all non-digit characters
    normalized_name = normalize_name(abook_entry.get('name', ''))
    normalized_emails = set([
        normalize_email(email)
        for email in abook_entry.get('email', []) if email
    ])
    normalized_phones = set([
        normalize_phone(phone)
        for field in phone_fields
        for phone in abook_entry.get(field, [])
    ])
    return normalized_name, normalized_emails, normalized_phones


def write_entry_to_abook(f, entry, header):
    """Write a single entry to an abook addressbook file."""
    f.write(f'[{header}]\n')
    for key, value in entry.items():
        if not value:
            continue
        if isinstance(value, list):
            value = ','.join(value)
        f.write(f'{key}={value}\n')
    f.write('\n')


def write_dictlist_to_abook(file_path, format_entry, entries):
    """Convert a list of dictionaries to an abook addressbook file."""
    with open(file_path, 'w') as f:
        if format_entry:
            write_entry_to_abook(f, format_entry, 'format')
        for i, entry in enumerate(entries):
            write_entry_to_abook(f, entry, i)


def find_matching_abook_entries(google_entry, abook_entries):
    """Find a matching abook entry for a given google entry."""

    google_name, google_emails, google_phones = get_normalized_values(
        google_entry
    )
    matching_entries = []
    for abook_entry in abook_entries:
        abook_name, abook_emails, abook_phones = get_normalized_values(
            abook_entry
        )
        name_match = google_name and abook_name and google_name == abook_name
        email_match_count = sum(
            1 for email in google_emails if email in abook_emails
        )
        phone_match_count = sum(
            1 for phone in google_phones if phone in abook_phones
        )

        if (
            name_match and email_match_count == len(google_emails) and
            phone_match_count == len(google_phones)
        ):
            return MatchType.FULL_MATCH, abook_entry
        elif name_match or email_match_count > 0 or phone_match_count > 0:
            matching_entries.append(abook_entry)

    if matching_entries:
        return MatchType.PARTIAL_MATCH, matching_entries
    else:
        return MatchType.UNMATCHED, None


def update_abook_entry(abook_entry, google_entry):
    """Update an abook entry with information from a google entry."""
    google_name = normalize_name(google_entry.get('name', ''))
    abook_name, abook_emails, abook_phones = get_normalized_values(
        abook_entry
    )
    if google_name:
        if not abook_name:
            abook_entry['name'] = google_entry['name']
        elif google_name != abook_name:
            # Ask the user if they want to update the name
            print(
                "Do you want to update the name from "
                f"'{abook_entry['name']}' to '{google_entry['name']}'? (y/n)"
            )
            user_input = input().strip().lower()
            if user_input == 'y':
                abook_entry['name'] = google_entry['name']
    for key in email_phone_fields:
        # Do not change original order, only append new values
        # Do not add a phone number that exists even in a different phone_field
        check_set = abook_emails if key == 'email' else abook_phones
        for value in google_entry.get(key, []):
            normalized_value = (
                normalize_email(value) if key == 'email'
                else normalize_phone(value)
            )
            if normalized_value not in check_set:
                abook_entry.setdefault(key, []).append(value)
                check_set.add(normalized_value)


def update_abook_entries(abook_entries, google_entries):
    """Update abook entries with information from google entries."""
    for google_entry in google_entries:
        if not google_entry.get('name') or not any(
            google_entry.get(field) for field in email_phone_fields
        ):
            continue
        match_type, matching_entries = find_matching_abook_entries(
            google_entry, abook_entries
        )

        if match_type == MatchType.UNMATCHED:
            print(f"Unmatched entry: {google_entry}")
            print("Do you want to add this entry to abook? (y/n)")
            user_input = input().strip().lower()
            if user_input == 'y':
                abook_entries.append(google_entry)
                print("Entry added.")
            else:
                print("Entry not added.")
        elif match_type == MatchType.PARTIAL_MATCH:
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
                update_abook_entry(entry_to_update, google_entry)
            elif user_input == 'a':
                abook_entries.append(google_entry)
                print("Entry added.")


if __name__ == "__main__":
    # Read the abook addressbook file
    abook_file_path = os.path.expanduser("~/.abook/addressbook")
    format_entry, abook_entries = read_abook_to_dictlist(abook_file_path)
    print(f"Read {len(abook_entries)} entries from abook addressbook.")

    # Read the google contacts csv file and convert to simplified abook format
    google_contacts_file_path = os.path.expanduser("/tmp/contacts.csv")
    google_entries = read_google_contacts_to_dictlist(
        google_contacts_file_path
    )
    google_abook_entries = [
        convert_google_entry_to_abook_entry(entry) for entry in google_entries
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
