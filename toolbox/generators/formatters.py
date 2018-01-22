import io
import csv
from tempfile import NamedTemporaryFile
from math import ceil
from string import ascii_uppercase
from operator import itemgetter
import pprint


class FileFormat(object):
    def __init__(self, plates, substances, ordering=None, write_to=None):
        self.plates = plates
        self.substances = substances
        self.write_to = write_to
        self.output_files = {}
        self.ordering = ordering
        self.make_file()

    def char_to_num(self, char):
        return ascii_uppercase.index(char) + 1

    def get_file(self):
        if self.write_to:
            return NamedTemporaryFile(mode='w', dir=self.write_to, delete=False)
        return io.StringIO()

    def get_locations(self):
        locations = {}
        for plate in filter(lambda x: x.function != 'destination', self.plates):
            filled = plate.get_filled_wells()
            for loc, well in filled.items():
                locations[well.contents[0].substance.name] = [plate.location, list(loc)[0],
                                                              list(loc)[1]]
        return locations

    @property
    def output(self):
        if self.write_to:
            data = {fn: f.name for fn, f in self.output_files.items()}
        else:
            data = self.output_files
        return data

    def make_file(self):
        pass


class MosquitoFileFormat(FileFormat):

    HEADERS = ['Position', 'Column', 'Row', 'Position', 'Column', 'Row', 'Nanolitres', '', '']

    def make_row(self, amount, plate_location, well_location, substance_locations):
        rows = []
        source = substance_locations[amount.substance.name]
        if amount.amount > 1200:
            redistribute = ceil(amount.amount/1200)
            new_amount = ceil(amount.amount/redistribute)
            for i in range(0, redistribute):
                rows.append([source[0], source[2], self.char_to_num(source[1]),
                             plate_location, well_location[1], self.char_to_num(well_location[0]),
                             new_amount])
        else:
            rows.append([source[0], source[2], self.char_to_num(source[1]),
                         plate_location, well_location[1], self.char_to_num(well_location[0]),
                         amount.amount])
        return rows

    def make_file(self):
        substance_locations = self.get_locations()
        output_file = self.get_file()
        writer = csv.writer(output_file)
        worklist = []
        for plate in filter(lambda x: x.function == 'destination', self.plates):
            filled = plate.get_filled_wells()
            for loc, well in filled.items():
                for amount in well.contents:
                    worklist.extend(self.make_row(amount, plate.location,
                                                  loc, substance_locations))
        if self.ordering:
            worklist.sort(key=itemgetter(*self.ordering))
        writer.writerow(self.HEADERS)
        writer.writerow(['Worklist'] + [''] * (len(self.HEADERS) - 1))
        writer.writerows(worklist)
        self.output_files['worklist'] = output_file


class EchoFileFormat(FileFormat):

    HEADERS = ['Source Barcode', 'Source', 'Destination Barcode', 'Destination', 'Volume']

    def make_file(self):
        substance_locations = self.get_locations()
        output_file = self.get_file()
        writer = csv.writer(output_file)
        worklist = []
        for plate in filter(lambda x: x.function == 'destination', self.plates):
            filled = plate.get_filled_wells()
            for loc, well in filled.items():
                for amount in well.contents:
                    source = substance_locations[amount.substance.name]
                    worklist.append([source[0], '{}{}'.format(source[1], source[2]),
                                     plate.location, '{}{}'.format(loc[0], loc[1]), amount.amount])
        if self.ordering:
            worklist.sort(key=itemgetter(*self.ordering))
        writer.writerow(self.HEADERS)
        writer.writerows(worklist)
        self.output_files['worklist'] = output_file


class FelixFileFormat(FileFormat):

    HEADERS_REACTION = ['Reaction_Number', 'Sample_Name', 'Volume']
    HEADERS_SOURCE = ['Well', 'Sample_Name']

    def make_file(self):
        substance_locations = self.get_locations()

        reactions_file = self.get_file()
        source_file = self.get_file()

        reaction_writer = csv.writer(reactions_file)
        reaction_worklist = []
        reaction_number = 1
        for plate in filter(lambda x: x.function == 'destination', self.plates):
            filled = plate.get_filled_wells()
            for loc, well in filled.items():
                # REACTION
                reaction_worklist.append([reaction_number, 'REACTION', well.total()])
                for amount in well.contents:
                    if amount.substance.name == 'Master Mix':
                        reaction_worklist.append([reaction_number, 'MIX', amount.amount])
                    elif amount.substance.name != 'Water':
                        reaction_worklist.append([reaction_number, amount.substance.name,
                                                  amount.amount])
                reaction_number += 1
        if self.ordering:
            reaction_worklist.sort(key=itemgetter(*self.ordering))
        reaction_writer.writerow(self.HEADERS_REACTION)
        reaction_writer.writerows(reaction_worklist)
        self.output_files['reactions'] = reactions_file

        source_writer = csv.writer(source_file)
        source_worklist = []
        for plate in filter(lambda x: x.label == 'Parts', self.plates):
            filled = plate.get_filled_wells()
            for loc, well in filled.items():
                source_worklist.append(["{}{}".format(*loc), well.contents[0].substance.name])
        source_writer.writerow(self.HEADERS_SOURCE)
        source_writer.writerows(source_worklist)
        self.output_files['sources'] = source_file

