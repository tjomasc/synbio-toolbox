from math import ceil
from functools import reduce
from operator import attrgetter

from .generators import Generator, Plate, Amount, Substance


class LibraryPoolingGenerator(Generator):

    def __init__(self, *args, **kwargs):
        self.ordering = [0,1]
        super().__init__(*args, **kwargs)

    def setup(self, **kwargs):
        number_of_wells = int(kwargs.get('number_of_wells', 96))

        if not 'volumes' in self.supplied_files:
            raise Exception('Missing volumes file')
        volumes_file = self.validate_csv_file(self.supplied_files['volumes'],
                                              ('source plate', 'source well', 'sample ID',
                                               'volume', 'destination well'),
                                              'Volumes')

        pooling_plate = Plate(number_of_wells, 'Pools',
                              kwargs.get('pooling_location', 3), function='destination')
        self.plates.extend([pooling_plate])

        # Sort file by destination as to group pooled samples into same
        volumes_file = sorted(volumes_file, key=lambda x: x['destination well'])

        for sample in volumes_file:
            if reduce(lambda x, y: x + y, sample.values()) != '':
                sample_name = sample['sample ID']

                if int(sample['source plate']) == 3:
                    raise Exception('Source plates cannot be placed in position 3')
                try:
                    samples_plate = next((x for x in self.plates
                                          if x.location == sample['source plate']))
                except:
                    samples_plate = Plate(number_of_wells, 'Source '+sample['source plate'],
                                          sample['source plate'], function='source')
                    self.plates.extend([samples_plate])

                try:
                    sub = self.substances[sample_name]
                except KeyError:
                    sub = Substance(sample_name)
                    self.substances[sample_name] = sub
                    volume = ceil(float(sample['volume']) * 1000)
                    if len(samples_plate.get_well(sample['source well']).contents) > 0:
                        raise Exception('Well {} in plate {} contains multiple samples. Check file.'
                                        .format(sample['source well'], sample['source plate']))
                    samples_plate.add_amount(sample['source well'], volume, sub)

                well = pooling_plate.get_well(sample['destination well'])
                well.add(volume, sub)
