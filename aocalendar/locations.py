import astropy.units as u
from astropy.coordinates import EarthLocation
import json


LOCATIONS = {
    'ata': EarthLocation(lat=40.817431*u.deg, lon=-121.470736*u.deg, height=1019*u.m)
}


class Location:
    def __init__(self, name=None, loc=None, lat=None, lon=None, height=None):
        self.get_location(name=name, loc=loc, lat=lat, lon=lon, height=height)

    def get_location(self, name=None, loc=None, lat=None, lon=None, height=None):
        self.valid = True
        if isinstance(name, Location):
            self.name = name.name
            self.loc = name.loc
            self.lat = name.lat
            self.lon = name.lon
            self.height = name.height
            return

        if isinstance(name, str) and name.lower() in LOCATIONS:
            loc =  LOCATIONS[name.lower()]

        if isinstance(loc, EarthLocation):
            self.name = name
            self.loc = loc
            self.lat = loc.lat.value
            self.lon = loc.lon.value
            self.height = loc.height.value
            return

        if loc is None and lat is None and isinstance(name, str):
            loc = json.loads(name)
        if isinstance(loc, str):
            loc = json.loads(loc)
        if isinstance(loc, dict):
            self.lat, self.lon, self.height = float(loc['lat']), float(loc['lon']), float(loc['height'])
            self.loc = EarthLocation(lat=self.lat*u.deg, lon=self.lon*u.deg, height=self.height*u.m)
            self.name = loc['name']
            return
        height = 0.0 if height is None else height
        try:
            self.lat, self.lon, self.height = float(lat), float(lon), float(height)
            self.loc = EarthLocation(lat=self.lat*u.deg, lon=self.lon*u.deg, height=self.height*u.m)
        except ValueError:
            self.valid = False
        self.name = name

    def stringify(self):
        return json.dumps({'name': self.name, 'lat': self.lat, 'lon': self.lon, 'height': self.height})