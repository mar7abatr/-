import json
from shapely.geometry import shape, Point
gov = {f['properties']['name']: shape(f['geometry']) for f in json.load(open('geo/irq_adm1.json'))['features']}
for name in ['Sala ad-Din', "At-Ta'mim"]:
    g = gov[name]
    print(name, g.bounds)
    for lat in [35.8, 35.6, 35.4, 35.2, 35.0, 34.8, 34.6, 34.4, 34.2, 34.0]:
        row = ''.join('#' if g.contains(Point(lon / 10, lat)) else '.' for lon in range(425, 460, 1))
        print(f'{lat:5.1f}', row)
