import csv

from .converters import Converter


class ListToPlateConverter(Converter):
    def setup(self, **kwargs):
        self.plate = [[""] * 12 for i in range(8)]
        self.letters = [chr(i) for i in range(65, 73)]

    def generate(self):
        if not 'list' in self.input_files:
            raise Exception('Missing list file')
        list_file = csv.reader(self.input_files['list'])
        # Skip the first header row
        next(list_file)
        for row in list_file:
            r = ord(row[0][0]) - 65
            c = int(row[0][1:]) - 1
            try:
                self.plate[r][c] = row[1]
            except IndexError:
                raise Exception('Invalid location specified')
        return {'plate': self.plate, 'letters': self.letters}
