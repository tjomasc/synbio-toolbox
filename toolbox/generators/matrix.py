import csv
from math import ceil
from functools import reduce
from operator import attrgetter
from string import ascii_uppercase

from .generators import Generator, Plate, Amount, Substance


class PlateMatrixGenerator(Generator):

    def __init__(self, *args, **kwargs):
        self.ordering = [0,1]
        super().__init__(*args, **kwargs)

    def setup(self, **kwargs):
        number_of_wells = int(kwargs.get('number_of_wells', 384))
        amount_substance = float(kwargs.get('amount_substance', 50))
        amount_mix = float(kwargs.get('amount_mix', 50)) * 1000
        default_mix = kwargs.get('default_mix', None)

        initial_mix_amount = 10000

        if number_of_wells == 384:
            rows = 16
            cols = 24
        else:
            rows = 8
            cols = 12

        if not 'sources' in self.supplied_files:
            raise Exception('Missing source locations file')

        if not 'matrix' in self.supplied_files:
            raise Exception('Missing plate matrix file')

        sources_file = self.validate_csv_file(self.supplied_files['sources'],
                                              ('plate', 'well', 'identifier'),
                                              'Sources')
        try:
            matrix_file = csv.reader(self.supplied_files['matrix'])
            matrix_list = list(matrix_file)
        except:
            raise Exception('Plate matrix is not a valid CSV file')

        # Parse source plates
        for source in sources_file:
            sub = Substance(source['identifier'])
            self.substances[source['identifier']] = sub
            try:
                source_plate = next((plate for plate in self.plates
                                        if plate.location == int(source['plate'])))
            except:
                source_plate = Plate(number_of_wells, 'Sources',
                                     int(source['plate']), function='source')
                self.plates.extend([source_plate])
            source_plate.add_amount(source['well'], initial_mix_amount, sub)

        destination_plate = Plate(number_of_wells, 'Destination',
                                  int(kwargs.get('destination_location', 5)),
                                  function='destination')
        self.plates.extend([destination_plate])

        for row in range(rows):
            letter = ascii_uppercase[int(row)]
            for col in range(1, cols + 1):
                cell = matrix_list[row][col-1]
                name, p, mix = cell.rstrip(')').partition('(')
                name = name.strip()

                try:
                    sub = self.substances[name]
                except KeyError as e:
                    raise Exception('Source location for {} not available!'.format(name))

                mix_sub = None
                if mix:
                    mix = mix.strip()
                    try:
                        mix_sub = self.substances[mix]
                    except KeyError:
                        raise Exception('Mix location for {} not available!'.format(mix))
                else:
                    if default_mix:
                        mix_sub = self.substances[default_mix]

                well = destination_plate.get_well('{}{}'.format(letter, col))
                well.add(amount_substance, sub)
                if mix_sub:
                    well.add(amount_mix, mix_sub)
