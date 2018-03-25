# Reverse geocoder for photography

This tools uses Nominatim to reverse geocode photos (i.e. put location names on coordinates of a photo). It tries its best to map is to the Metadata Working Group location fields. Then it stores the output in a sidecar XMP file.

# Prerequisite
* [exiftool](https://sno.phy.queensu.ca/~phil/exiftool/)
* Python 3.5+ (tested on Python 3.6.4)

# Installing the dependencies
In the list below, replace pip3 by pip if Python 3 is your default installation

```
pip3 install -r requirements.txt
```

# How to geotag your photos?
This has to be geotag prior to using this tool. You can use [exiftool to perform this task](https://sno.phy.queensu.ca/~phil/exiftool/geotag.html)

## Tip for Olympus
Recent Olympus cameras (tested on OM-D E-M5 Mk2) have a DateTimeUTC which greatly simplifies this process:
```
exiftool -geotag $GPX_FILE '-geotime<${DateTimeUTC}+00:00' -P *.ORF -srcfile %d%f.xmp -srcfile @
```
You have to replace $GPX_FILE by the location of the GPX track.

# Using the tool
```
# If your coordinates are stored in XMP sidecar files, use this:
python3 /path/to/geocode.py *.xmp

# If your coordinates are stored in NEF file, it will create .XMP as output
python3 /path/to/geocode.py *.NEF

# Adapt to your own file format!

# You can also use individual files:
python3 /path/to/geocode.py abc.NEF def.CR2
```

# Thanks
This tool has been started from: [podiki's work](https://github.com/podiki/reverse_geo).
