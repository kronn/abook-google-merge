# abook-google-merge

**Update an [abook](http://abook.sourceforge.net/) addressbook with contacts and details exported from Google Contacts.**

`abook-google-merge` reads an existing `abook` addressbook and a csv of contacts exported from Google Contacts. It then matches contacts crudely by name, email and phone number, and walks you through adding new contacts and filling in missing emails and phone numbers on entries you already have.

## Dependencies

`abook-google-merge` is written in Python 3 and only uses the standard library, so there is nothing else to install.

## Installation

```bash
git clone https://github.com/razimantv/abook-google-merge
cd abook-google-merge
```


No build step is needed, just run the script directly with Python.

## Usage
```
Usage: python3 main.py [-h] [-i <abook file>] [-g <google csv file>] [-o <output file>]

Options:
  -h, --help          Show this message and exit
  -i, --input  INPUT  Path to the abook file (default: ~/.abook/addressbook)
  -g, --google GOOGLE Path to the google contacts csv file (default: google.csv)
  -o, --output OUTPUT Path to the output file (default: overwrite the input file)
```

## Functionality

For each contact in the Google export, abook-google-merge looks for a matching
entry in the abook file:

- Contacts that already fully match an existing entry (that is, the name matches while all the phone and email fields are already present in the entry) are left untouched, since there is nothing new to add.
- If no fields match, you're asked whether to add it as a new entry.
- If a partial match is found (same name, email or phone number, but something differs), you're shown the candidate entries and asked whether to update one of them, add the Google contact as a new entry, or skip it.
- Faulty entries (missing name, or missing both email and phone number) are ignored.

If the output path is the same as the input (the default), the original file is backed up with a `.bak` suffix before being overwritten.

## Limitations

- The program is written for my use case, so it may not work exactly as you intend. In particular,
    - All fields other than name, email, and phone number fields in Google Contacts are ignored (but the extra fields in the abook file are unchanged).
    - Phone number comparison is quite crude and does not identify the same number written with and without a country code as a match. For example, `+91 31415 92653` and `031 4159 2653` will not be recognised as the same number.
    - I have assumed reasonable sizes for the address books, so the comparison algorithms are not turbo efficient.

If you find some design choice that is too limiting, please raise an issue (or even better, a pull request) and I will try to address it.
