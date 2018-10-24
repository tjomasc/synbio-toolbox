from math import ceil
from functools import reduce

from .generators import Generator, Plate, Amount, Substance
from .headers import CONSTRUCTS_CSV, PARTS_CSV, PARTS_LOCATION_CSV


class PartPoolingGenerator(Generator):

    def __init__(self, *args, **kwargs):
        self.ordering = [0,1]
        super().__init__(*args, **kwargs)

    def setup(self, **kwargs):
        """
        Create a DNA part pooling setup.
        """
        # what files are needed and are they correct?
        # What variables are needed and are they correct?
        number_of_wells = int(kwargs.get('number_of_wells', 96))
        amount_of_part = float(kwargs.get('amount_of_part', '10'))
        amount_of_backbone = float(kwargs.get('amount_of_backbone', '40'))
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
        self.other_files['new_volumes'] = {}

        # Create plate defs
        reagents_plate = Plate(number_of_wells, 'Reagents', kwargs.get('reagents_location', 1))
        # Create substance types
        water = Substance('Water')
        master_mix = Substance('Master Mix')
        self.substances['Water'] = water
        self.substances['Master Mix'] = master_mix

        reagents_plate.add_amount(kwargs.get('water_well', 'A1'), 0, water)
        reagents_plate.add_amount(kwargs.get('master_mix_well', 'B1'), 0, master_mix)

        parts_plate = Plate(number_of_wells, 'Parts', kwargs.get('parts_location', 2))
        constructs_plate = Plate(number_of_wells, 'Constructs',
                                 kwargs.get('constructs_location', 3),
                                 function='destination',
                                 placement=kwargs.get('placement', 'row'))

        self.plates.extend([reagents_plate, parts_plate, constructs_plate])

        well = constructs_plate.get_well(self.current_well)
        for construct in constructs_file:
            # Ignore empty lines
            if reduce(lambda x, y: x + y, construct.values()) != '':
                for location, part_name in construct.items():
                    if location in CONSTRUCTS_CSV and part_name != '' and location != 'Master Mix':
                        try:
                            part = part_data[part_name]
                        except KeyError:
                            raise Exception('{} was not supplied in the parts file' \
                                    .format(part_name))
                        try:
                            part_coordinates = part_locations[part['Barcode']]
                        except KeyError:
                            raise Exception('{} was not supplied a location'.format(part_name))

                        try:
                            sub = self.substances[part_name]
                        except KeyError:
                            sub = Substance(part_name)
                            self.substances[part_name] = sub
                            volume = float(part['Volume']) * 1000
                            parts_plate.add_amount(part_coordinates, volume, sub)

                        if location == 'Backbone':
                            part_volume = ceil(amount_of_backbone / float(part['Concentration']) \
                                          * 1000)
                        else:
                            part_volume = ceil(amount_of_part / float(part['Concentration']) \
                                          * 1000)

                        if part_volume <= 25:
                            raise Exception('Volume {} to small for construct {}' \
                                            .format(part_volume, part_name))

                        well.add(part_volume, sub)

                        # Calculate new volumes file
                        if part_name in self.other_files['new_volumes']:
                            curr_volume = self.other_files['new_volumes'][part_name]['new_volume']
                            new_volume = ((curr_volume * 1000) - part_volume) / 1000;
                            self.other_files['new_volumes'][part_name]['new_volume'] = new_volume
                        else:
                            new_volume = ((float(part['Volume']) * 1000) - part_volume) / 1000;
                            self.other_files['new_volumes'][part_name] = {
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
