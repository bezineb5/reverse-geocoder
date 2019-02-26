import argparse
import glob
import concurrent.futures
import logging
import os
import threading

import exiftool
from geopy.geocoders import Nominatim

log = logging.getLogger(__name__)
exiftool_lock = threading.Lock()

# Dictionary of tags for ExifTool locations to data from geopy
# Made with the help of: https://github.com/OpenCageData/address-formatting/blob/master/conf/components.yaml
NOMINATIM_MAPPING = {'MWG:Country': ['country', 'country_name'],
                     'MWG:State': ['state', 'province', 'region', 'island', 'state_code', 'state_district', 'county', 'county_code'],
                     'MWG:City': ['city', 'town', 'village', 'hamlet', 'locality', 'neighbourhood', 'suburb', 'city_district']}


def _parse_arguments():
    parser = argparse.ArgumentParser(description='Simple reverse geocoding with geopy and exiftool')
    parser.add_argument('files', nargs='+', help='files to reverse geocode')
    files = parser.parse_args().files
    return files


def _map_nominatim_place_to_tags(raw_place):
    display_name = raw_place.get('display_name')
    address = raw_place.get('address')

    params = []
    for tag, v in NOMINATIM_MAPPING.items():
        if isinstance(v, str):
            # Single value
            content = address.get(v)
            if content:
                params.append("-{tag}={content}".format(tag=tag, content=content))
        else:
            # List of values, by decrementing order of interest
            for key in v:
                content = address.get(key)
                if content:
                    params.append("-{tag}={content}".format(tag=tag, content=content))
                    break

    if display_name:
        components = display_name.split(', ')
        if components:
            house_number = address.get('house_number')
            if house_number and components[0] == house_number and len(components) > 1:
                params.append("-{tag}={content}".format(tag="MWG:Location", content=', '.join(components[0:2])))
            else:
                params.append("-{tag}={content}".format(tag="MWG:Location", content=components[0]))


    return params


def reverse_geocode(et, geolocator, f):
    # Find place names from GPS already in file
    # Note: use the XMP tags so that lat/long has a - sign for W or S
    log.info("Geocoding %s", f)
    with exiftool_lock:
        gps_dict = et.get_tags(['XMP:GPSLatitude', 'XMP:GPSLongitude', 'XMP:Country'], f)
    lat = gps_dict.get('XMP:GPSLatitude')
    lng = gps_dict.get('XMP:GPSLongitude')
    previous_country = gps_dict.get('XMP:Country')
    if not lat or not lng:
        log.info("Aborting, missing lat/long")
        return
    if previous_country:
        log.info("Aborting, previous country: %s", previous_country)
        return

    location = geolocator.reverse((lat, lng), exactly_one=True)

    if not location:
        return
    
    log.info(location.raw)
    nominatim_address = location.raw
    if not nominatim_address:
        return

    # Apply reverse geocoding using MWG tag standards
    # (see, e.g., http://www.metadataworkinggroup.org/ and
    # http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/MWG.html)
    # This works best for cities, for rural areas (e.g. when hiking) let's
    # use the county if available. Would be great to get more info, but for
    # now that works okay. There may be a lot of variation in what makes
    # sense, especially the Location tag, so may need to make this more
    # sophisticated in the future.
    params = _map_nominatim_place_to_tags(nominatim_address)

    # Then add the filename and encode everything
    params.append("-srcfile %d%f.xmp")
    params.append("-overwrite_original")
    params.append(f)

    # Do the tagging! It seems that execute_json fails in that case.
    params = map(os.fsencode, params)
    with exiftool_lock:
        log.info(et.execute(*params).decode("utf-8"))


def geocode_files(files, user_agent: str="https://github.com/bezineb5/reverse-geocoder"):
    all_files = []
    for file in files:
        all_files.extend(glob.glob(file))

    if not all_files:
        return

    # Use Nominatim, from OpenStreetMap, for reverse lookup
    geolocator = Nominatim(user_agent=user_agent)

    with exiftool.ExifTool() as et:
        def geocoding(f):
            try:
                reverse_geocode(et, geolocator, f)
            except Exception as e:
                log.exception("Error while geotagging: %s", f)
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            for f in all_files:
                executor.submit(geocoding, f)
            
            executor.shutdown()


def main():
    logging.basicConfig(level=logging.INFO)

    files = _parse_arguments()
    if not files:
        return

    geocode_files(files)


if __name__ == '__main__':
    main()
