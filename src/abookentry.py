from enum import Enum


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
        """ Enum for match types when comparing entries. """
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

    def add_email_if_new(self, email: str, label: str = 'email'):
        """
        Safely append a new email, updating both the raw list and the set.
        """
        normalized_email = AbookEntry.normalize_email(email)
        if normalized_email not in self._normalized_emails:
            self.fields.setdefault(label, []).append(email)
            self._normalized_emails.add(normalized_email)

    def add_phone_if_new(self, phone: str, label: str):
        """
        Safely append a new phone number to a specific label,
        updating both the raw list and the set.
        """
        normalized_phone = AbookEntry.normalize_phone(phone)
        if normalized_phone not in self._normalized_phones:
            self.fields.setdefault(label, []).append(phone)
            self._normalized_phones.add(normalized_phone)

    def __str__(self):
        """
        Return a string representation of the entry for debugging.
        """
        return f"{self.fields}"

    def get_match(self, other):
        """
        Compare this entry with another entry and return the match type.
        """
        name_match = (
            other._normalized_name and self._normalized_name and
            other._normalized_name == self._normalized_name
        )
        email_match_count = len(
            other._normalized_emails.intersection(
                self._normalized_emails
            )
        )
        phone_match_count = len(
            other._normalized_phones.intersection(self._normalized_phones)
        )

        if (
            name_match and
            email_match_count == len(other._normalized_emails) and
            phone_match_count == len(other._normalized_phones)
        ):
            return AbookEntry.MatchType.FULL_MATCH
        elif name_match or email_match_count > 0 or phone_match_count > 0:
            return AbookEntry.MatchType.PARTIAL_MATCH
        else:
            return AbookEntry.MatchType.UNMATCHED

    @staticmethod
    def _to_abook_entry_string(fields, header):
        """
        Convert entry to the abook addressbook format string, with header.
        """
        lines = [f'[{header}]']
        for key, value in fields.items():
            if value:
                if isinstance(value, list):
                    value = ','.join(value)
                lines.append(f'{key}={value}')
        return '\n'.join(lines) + '\n\n'

    def to_abook_entry_string(self, entry_id):
        """
        Convert entry to the abook addressbook format string, with header id.
        """
        return AbookEntry._to_abook_entry_string(self.fields, f'{entry_id}')

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

        for key in AbookEntry.email_fields:
            for value in other_entry.fields.get(key, []):
                self.add_email_if_new(value, key)

        for key in AbookEntry.phone_fields:
            for value in other_entry.fields.get(key, []):
                self.add_phone_if_new(value, key)
