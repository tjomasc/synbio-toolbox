import csv
from tempfile import NamedTemporaryFile
from string import ascii_uppercase


class Converter(object):

    def __init__(self, *args, **kwargs):
        # Any files required to generate the file(s)
        self.input_files = kwargs.get('files', {})
        # Build any data needed to run the converter
        self.setup(**kwargs)

    def setup(self, **kwargs):
        pass

    def generate(self):
        return None

    def validate_csv_file(self, file_object, headers, file_name):
        """
        Check a file is a valid CSV file with correct headers
        """
        csv_file = csv.DictReader(file_object)
        if csv_file.fieldnames is None:
            raise Exception('The {} file is invalid; No headers present.'.format(file_name))
        csv_headers = set(csv_file.fieldnames)
        required_headers = set(headers)
        has_headers = required_headers <= csv_headers
        missing_headers = required_headers - csv_headers
        if not has_headers:
            exception_text = 'The file {} is missing the following headers: {}' \
                .format(file_name, ", ".join(missing_headers))
            raise Exception(exception_text)
        return csv_file

    def get_file(self, write_to):
        if write_to:
            return NamedTemporaryFile(mode='w', dir=write_to, delete=False)
        return io.StringIO()

    def to_output_file(self, file_name, output, write_to=None):
        output_file = self.get_file(write_to)
        items = list(output.values())
        writer = csv.DictWriter(output_file, fieldnames=items[0].keys())
        writer.writeheader()
        writer.writerows(items)
        return (file_name, output_file)
