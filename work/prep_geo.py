import json
a1 = json.load(open('geo/adm1.geojson'))
irq = [f for f in a1['features'] if f['properties']['adm0_a3'] == 'IRQ']
for f in irq:
    p = f['properties']
    print(p['name'], '|', p.get('name_ar'), '|', p['latitude'], p['longitude'])
json.dump({'type': 'FeatureCollection', 'features': irq}, open('geo/irq_adm1.json', 'w'))
a0 = json.load(open('geo/adm0.geojson'))
keep = ['IRQ', 'IRN', 'SYR', 'TUR', 'SAU', 'KWT', 'JOR', 'ARM', 'AZE', 'LBN', 'ISR', 'PSX', 'PSE',
        'GEO', 'CYP', 'EGY', 'BHR', 'QAT', 'ARE']
f0 = [f for f in a0['features'] if f['properties']['ADM0_A3'] in keep]
print([(f['properties']['ADM0_A3'], f['properties'].get('NAME_AR')) for f in f0])
json.dump({'type': 'FeatureCollection', 'features': f0}, open('geo/countries.json', 'w'))
r = json.load(open('geo/rivers.geojson'))
rv = [f for f in r['features'] if f['properties'].get('name') in
      ('Tigris', 'Euphrates', 'Great Zab', 'Little Zab', 'Diyala', 'Shatt al Arab')]
print([f['properties']['name'] for f in rv])
json.dump({'type': 'FeatureCollection', 'features': rv}, open('geo/rivers_sel.json', 'w'))
