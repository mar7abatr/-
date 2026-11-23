import json, pickle, math
from shapely.geometry import shape, LineString, Polygon, MultiPolygon, box
from shapely.ops import unary_union

LAT0, LON0 = 31.42, 34.38
KX = math.cos(math.radians(LAT0)) * 111.32
KY = 110.57


def P(lon, lat):
    return ((lon - LON0) * KX, -(lat - LAT0) * KY)


def proj_geom(g):
    from shapely.ops import transform
    return transform(lambda x, y, z=None: P(x, y), g)


def rings(g):
    out = []
    polys = [g] if isinstance(g, Polygon) else list(getattr(g, "geoms", []))
    for p in polys:
        if p.is_empty:
            continue
        out.append([list(p.exterior.coords)] + [list(r.coords) for r in p.interiors])
    return out


# Region clip box (degrees)
REG = box(27.0, 26.0, 42.0, 37.0)
ne = json.load(open("/tmp/work/geo/ne_countries.geojson"))
countries = {}
for f in ne["features"]:
    nm = f["properties"].get("ADMIN")
    if nm in ("Israel", "Egypt", "Jordan", "Palestine", "Lebanon", "Syria", "Saudi Arabia", "Cyprus"):
        g = shape(f["geometry"]).intersection(REG)
        if not g.is_empty:
            countries[nm] = g

adm = json.load(open("/tmp/work/geo/pse_adm2.geojson"))
gaza_names = []
gov = {}
for f in adm["features"]:
    g = shape(f["geometry"])
    c = g.centroid
    if c.x < 34.6:  # Gaza Strip governorates are west of 34.6E
        gov[f["properties"]["shapeName"]] = g
print("gaza governorates:", list(gov))
strip = unary_union(list(gov.values())).buffer(0.0003).buffer(-0.0003)

# Land outside the strip (neighbours + West Bank); remove the NE Gaza part so the detailed strip replaces it
land = unary_union(list(countries.values())).difference(strip.buffer(0.002))

data = {
    "land": rings(proj_geom(land).simplify(0.25)),
    "borders": [],
    "strip": rings(proj_geom(strip).simplify(0.015)),
    "gov": [],
    "roads": [],
}
from shapely.geometry import LineString as LS
near_strip = strip.buffer(0.03)
for nm, g in countries.items():
    if nm == "Palestine":
        g = g.difference(near_strip)  # keep only the West Bank outline
    lines = g.boundary.difference(near_strip)
    for ln in getattr(lines, "geoms", [lines]):
        if ln.is_empty or ln.length == 0:
            continue
        c = list(proj_geom(ln).simplify(0.25).coords)
        if len(c) > 1:
            data["borders"].append(c)
# internal governorate boundaries as lines
for nm, g in gov.items():
    for r in rings(proj_geom(g).simplify(0.02)):
        data["gov"].append(r[0])

roads = json.load(open("/tmp/work/geo/roads.json"))
for e in roads["elements"]:
    if "geometry" not in e:
        continue
    pts = [P(p["lon"], p["lat"]) for p in e["geometry"]]
    if len(pts) < 2:
        continue
    ls = LineString(pts).simplify(0.01)
    data["roads"].append((e["tags"].get("highway"), list(ls.coords)))

b = proj_geom(strip).bounds
print("strip bounds km", [round(v, 2) for v in b])
H = {
    "nasser": (34.29229, 31.34703),
    "shifa": (34.44347, 31.52410),
    "kamal": (34.50128, 31.53848),
    "o_indonesian": (34.50922, 31.53510),
    "o_awda": (34.50665, 31.53382),
    "o_ahli": (34.46158, 31.50472),
    "o_rantisi": (34.46038, 31.53306),
    "o_quds": (34.43069, 31.50596),
    "o_aqsa": (34.35999, 31.41997),
    "o_european": (34.31985, 31.30363),
    "o_awda_nus": (34.38905, 31.45225),
    "o_yemen": (34.49626, 31.53636),
}
data["hosp"] = {k: P(*v) for k, v in H.items()}
data["strip_label"] = P(34.395, 31.455)
for k, v in data["hosp"].items():
    print(k, [round(x, 2) for x in v])
pickle.dump(data, open("/tmp/work/geo/map.pkl", "wb"))
print("land rings", len(data["land"]), "roads", len(data["roads"]))
