import csv
from tempfile import NamedTemporaryFile
from string import ascii_uppercase

from .formatters import MosquitoFileFormat, EchoFileFormat, FelixFileFormat


class Generator(object):

    def __init__(self, *args, **kwargs):
        # Any files required to generate the file(s)
        self.supplied_files = kwargs.get('supplied_files', {})
        # Starting well coordinates
        self.current_well = kwargs.get('starting_well', 'A1')
        # Write files to given location. Default to return as StringIO.
        self.write_to = kwargs.get('write_to', None)
        # Any other files that are required e.g. extra info
        self.other_files = {}
        # Master list of all substances in wells
        self.substances = {}
        # List of plates needed for the process to take place
        self.plates = []
        # Build the data needed to generate the file
        self.setup(**kwargs)

    def setup(self, **kwargs):
        pass

    def generate(self, equipment_format):
        output_files = []
        if equipment_format == 'mosquito':
            f = MosquitoFileFormat(self.plates, self.substances,
                                   ordering=self.ordering, write_to=self.write_to)
        elif equipment_format == 'echo':
            f = EchoFileFormat(self.plates, self.substances,
                               ordering=self.ordering, write_to=self.write_to)
        elif equipment_format == 'felix':
            f = FelixFileFormat(self.plates, self.substances,
                                ordering=self.ordering, write_to=self.write_to)
        else:
            raise Exception('File format not recognised')

        other_files = []
        # Loop through and build other files
        for file_name, output in self.other_files.items():
            created_file = self.to_output_file(file_name, output, write_to=self.write_to)
            if self.write_to:
                other_files.append((created_file[0], created_file[1].name))
            else:
                other_files.append(created_file)
        # Make plate diagram data
        plate_data = self.make_plate_layout_data()

        return f.output, other_files, plate_data

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

    def make_plate_layout_data(self):
        layout_data = {'plates': []}
        layout_data['substances'] = [s for s in self.substances]
        for p in self.plates:
            well_data = []
            for coord, well in p.wells.items():
                contents = [(a.amount, a.substance.name) for a in well.contents]
                well_data.append({
                    'coord': coord,
                    'contents': contents,
                    'total': well.total(),
                })
            layout_data['plates'].append({
                'label': p.label,
                'location': p.location,
                'well_count': p.well_count,
                'layout': p.layout,
                'function': p.function,
                'spacing': p.spacing,
                'wells': well_data,
            });
        return layout_data


class Substance(object):

    def __init__(self, substance_name, group=None):
        self.name = substance_name
        self.group = None

    def __str__(self):
        return self.name


class Amount(object):

    def __init__(self, amount, substance):
        self.amount = amount
        self.substance = substance


class Well(object):

    max_96 = 100000
    max_384 = 30000

    def __init__(self, *args, **kwargs):
        self.contents = []

    def add(self, value, substance):
        self.contents.append(Amount(value, substance))

    def total(self):
        total = 0
        for item in self.contents:
            total += item.amount
        return total


class Plate(object):

    plate_96 = (12, 8)
    plate_384 = (24, 16)

    def __init__(self, well_count, label, location, function='source', spacing=1,
                 placement='row', **kwargs):
        self.well_count = well_count
        # Nice easy to read name
        self.label = label
        # The location on the deck/placement etc.
        self.location = location
        # Either source or destination
        self.function = function
        # Gap between wells. 1 = normal, 2 = double, 3 = triple). Both directions.
        self.spacing = spacing
        # Set placement - row or column
        self.placement = placement

        self.wells = {}

        if self.well_count == 96:
            self.divisor = self.plate_96[0]
            self.layout = self.plate_96
        elif self.well_count == 384:
            self.divisor = self.plate_384[0]
            self.layout = self.plate_384

        self._make_wells()

    def _make_wells(self):
        """
        Build a list of wells, set indexed by A1 notation
        """
        w = 1
        for i in range(0, self.well_count):
            if i % self.divisor == 0:
                letter = ascii_uppercase[int(i/self.divisor)]
                w = 1
            self.wells[(letter, w)] = Well()
            w += 1

    def _to_well_coord(self, coord_string):
        return (coord_string[0], int(coord_string[1:]))

    def get_well(self, location):
        lookup = self._to_well_coord(location)
        try:
            well = self.wells[lookup]
        except KeyError as e:
            raise Exception('Location chosen is out of range')
        return well

    def get_next_well(self, previous_coordinates):
        row = ascii_uppercase.index(previous_coordinates[0])
        col = int(previous_coordinates[1:])
        if self.placement == 'column':
            # Select next well by column (going down the plate)
            if (row != 0 and (row + self.spacing) % self.layout[1] == 0) or row > self.layout[1]:
                next_row = ascii_uppercase[0]
                next_col = col + self.spacing
            else:
                next_row = ascii_uppercase[row + self.spacing]
                next_col = int(previous_coordinates[1])
        else:
            # Select next well by row (across the plate)
            if col % self.divisor == 0 or col > self.divisor:
                next_row = ascii_uppercase[row + self.spacing]
                next_col = self.spacing
            else:
                next_row = previous_coordinates[0]
                next_col = col + self.spacing
        lookup = (next_row, next_col)
        try:
            well = self.wells[lookup]
        except KeyError as e:
            raise Exception('Location chosen is out of range')
        return well, '{}{}'.format(next_row, next_col)

    def to_well_coord(self, row, col):
        string_row = ascii_uppercase[row + self.spacing]
        return '{}{}'.format(string_row, col)

    def get_filled_wells(self):
        filled = {}
        for coord, well in self.wells.items():
            if len(well.contents) > 0:
                filled[coord] = well
        return filled

    def add_amount(self, location, value, substance):
        well = self.get_well(location)
        well.contents.append(Amount(value, substance))
