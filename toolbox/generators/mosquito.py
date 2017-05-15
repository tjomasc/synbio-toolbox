from math import ceil
from functools import reduce

from .generators import Generator, Plate, Amount, Substance
from .headers import CONSTRUCTS_CSV, PARTS_CSV, PARTS_LOCATION_CSV


class MosquitoGenerator(Generator):

    def __init__(self, function, supplied_files, *args, **kwargs):
        self.function = function
        self.supplied_files = supplied_files
        super().__init__(*args, **kwargs)

    def setup(self, **kwargs):
        """
        Check what functionality is required and setup required plates
        """
        if self.function == 'dna_part_pooling':
            self._dna_part_pooling(**kwargs)
        else:
            raise Exception('Invalid process to generate file for')

    def _dna_part_pooling(self, **kwargs):
        """
        Create a DNA part pooling setup.
        """
        # what files are needed and are they correct?
        # What variables are needed and are they correct?
        number_of_wells = int(kwargs.get('number_of_wells', 96))
        amount_of_part = float(kwargs.get('amount_of_part', '10'))
        final_reaction_volume = float(kwargs.get('final_reaction_volume', 10))

        required_files = set(['constructs_file', 'parts_file', 'parts_location_file'])
        if not required_files == set(self.supplied_files.keys()):
            raise Exception('Missing required files')
        constructs_file = self.validate_csv_file(self.supplied_files['constructs_file'],
                                                 CONSTRUCTS_CSV,
                                                 'Constructs')
        parts_file = self.validate_csv_file(self.supplied_files['parts_file'],
                                            PARTS_CSV,
                                            'Parts')
        parts_location_file = self.validate_csv_file(self.supplied_files['parts_location_file'],
                                                     PARTS_LOCATION_CSV,
                                                     'Parts location')

        part_locations = {l['barcode'].strip(): l['location'].strip() for l in parts_location_file}
        part_data = {p['Part Name'].strip(): p for p in parts_file}

        # Register the output files
        self.output_files['new_volumes'] = {}

        # Create plate defs
        reagents_plate = Plate(number_of_wells, 'Reagents')
        # Create substance types
        water = Substance('Water')
        master_mix = Substance('Master Mix')
        self.substances['Water'] = water
        self.substances['Master Mix'] = master_mix

        reagents_plate.add_amount(kwargs.get('water_well'), 0, water)
        reagents_plate.add_amount(kwargs.get('master_mix_well'), 0, master_mix)

        parts_plate = Plate(number_of_wells, 'Parts')
        constructs_plate = Plate(number_of_wells, 'Constructs', function='destination')

        self.plates.append(reagents_plate, parts_plate, constructs_plate)

        well = constructs_plate.get_well(self.current_well)
        for construct in constructs_file:
            # Ignore empty lines
            if reduce(lambda x, y: x + y, construct.values()) != '':
                for location, part_name in construct.items():
                    if location in CONSTRUCTS_CSV and part_name != '' and location != 'Master Mix':
                        try:
                            sub = self.substances[part_name]
                        except KeyError:
                            sub = Substance(part_name)
                            self.substances[part_name] = sub
                        try:
                            part = part_data[part_name]
                        except KeyError:
                            raise Exception('{} was not supplied in the parts file' \
                                    .format(part_name))
                        try:
                            part_coordinates = part_locations[part['Barcode']]
                        except KeyError:
                            raise Exception('{} was not supplied a location'.format(part_name))

                        part_volume = ceil(amount_of_part / float(part['Concentration']) * 1000)

                        if part_volume <= 25:
                            raise Exception('Volume {} to small for construct {}' \
                                            .format(part_volume, part_name))

                        well.add(part_volume, sub)

                        # Calculate new volumes file
                        if part_name in self.output_files['new_volumes']:
                            curr_volume = self.output_files['new_volumes'][part_name]['new_volume']
                            new_volume = ((curr_volume * 1000) - part_volume) / 1000;
                            self.output_files['new_volumes'][part_name]['new_volume'] = new_volume
                        else:
                            new_volume = ((float(part['Volume']) * 1000) - part_volume) / 1000;
                            self.output_files['new_volumes'][part_name] = {
                                'part_name': part_name,
                                'barcode': part['Barcode'],
                                'old_volume': part['Volume'],
                                'new_volume': new_volume,
                            }

                    elif location == 'Master Mix':
                        master_mix_volume = float(part_name) * 1000
                        well.add(master_mix_volume, master_mix)
                # Now add the water to make it up to final reaction volume
                reaction_volume = well.total()
                water_volume = (final_reaction_volume * 1000) - reaction_volume
                if water_volume < 0:
                    raise Exception('Final reaction volume is larger than specified')
                well.add(water_volume, water)
                # Increment to next well
                well, coordinates = constructs_plate.get_next_well(self.current_well)
                self.current_well = coordinates

    def generate(self):
        pass
