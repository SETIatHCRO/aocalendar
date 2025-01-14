import astropy.units as u
from astropy.coordinates import EarthLocation
import json


LOCATIONS = {
    'ata': EarthLocation(lat=40.817431*u.deg, lon=-121.470736*u.deg, height=1019*u.m)
}


def location(name, lat=None, lon=None, height=None):
    if name is None:
        return None
    height = 0.0 if height is None else height
    if isinstance(name, EarthLocation):
        try:
            nn = getattr(name, "name")
        except AttributeError:
            name.name = "None"
        return name

    if isinstance(name, str) and name.lower() in LOCATIONS:
        site =  LOCATIONS[name.lower()]
        site.name = name
        return site

    try:
        if isinstance(name, str):
            name = json.loads(name)
    except (json.JSONDecodeError, TypeError):
        pass
    if isinstance(name, dict):
        try:
            nn = name['name']
        except AttributeError:
            name['name'] = "None"
        name['height'] = name['height'] if 'height' in name else 0.0
        lat, lon, height = float(name['lat']), float(name['lon']), float(name['height'])
        site = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=height*u.m)
        site.name = name
        return site

    site = EarthLocation(lat=float(lat)*u.deg, lon=float(lon)*u.deg, height=float(height)*u.m)
    site.name = name
    return site

def stringify(x):
    if not isinstance(x, EarthLocation):
        return None
    try:
        nn = getattr(x, "name")
    except AttributeError:
        x.name = "None"
    return json.dumps({'name': x.name, 'lat': x.lat.value, 'lon': x.lon.value, 'height': x.height.value})