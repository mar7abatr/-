import json, pickle, math
from shapely.geometry import shape, box, Polygon
from shapely.ops import unary_union, transform

LAT0, LON0 = 31.9, 35.25
KX = math.cos(math.radians(LAT0)) * 111.32
KY = 110.57

def P(lon, lat):
    return ((lon - LON0) * KX, -(lat - LAT0) * KY)

def proj(g):
    return transform(lambda x, y, z=None: P(x, y), g)

def rings(g):
    polys = [g] if isinstance(g, Polygon) else list(getattr(g, "geoms", []))
    return [[list(p.exterior.coords)] + [list(r.coords) for r in p.interiors] for p in polys if not p.is_empty]

REG = box(32.0, 28.6, 38.6, 35.2)
ne = json.load(open("geo/ne_countries.geojson"))
cs = {}
for f in ne["features"]:
    nm = f["properties"].get("ADMIN")
    if nm in ("Israel", "Egypt", "Jordan", "Palestine", "Lebanon", "Syria", "Saudi Arabia", "Cyprus"):
        g = shape(f["geometry"]).buffer(0).intersection(REG)
        if not g.is_empty:
            cs[nm] = g
print("countries", list(cs))

adm = json.load(open("geo/pse_adm2.geojson"))
govs = [shape(f["geometry"]).buffer(0) for f in adm["features"] if shape(f["geometry"]).centroid.x > 34.8]
wb = unary_union(govs).buffer(0.001).buffer(-0.001)
if not isinstance(wb, Polygon):
    wb = max(wb.geoms, key=lambda p: p.area)
land = unary_union(list(cs.values()) + [wb])

data = {"land": rings(proj(land).simplify(0.4)), "wb": rings(proj(wb).simplify(0.12)), "gov": [], "borders": []}
for g in govs:
    for r in rings(proj(g).simplify(0.15)):
        data["gov"].append(r[0])
for nm, g in cs.items():
    if nm == "Palestine":
        continue
    b = g.boundary
    for ln in getattr(b, "geoms", [b]):
        c = list(proj(ln).simplify(0.4).coords)
        if len(c) > 1:
            data["borders"].append(c)
c = proj(wb).centroid
data["wb_c"] = (c.x, c.y)
data["wb_bounds"] = proj(wb).bounds
# villages that repeatedly see settler attacks (OSM coordinates)
SPOTS = [(35.257, 32.152), (35.287, 32.037), (35.265, 32.031), (35.330, 32.000), (35.165, 31.400),
         (35.290, 32.140), (35.240, 32.170), (35.280, 32.070), (35.380, 32.060), (35.153, 32.219),
         (35.120, 31.390), (35.160, 31.690), (35.300, 31.990), (35.260, 31.980), (35.460, 31.950),
         (35.520, 32.300), (35.200, 31.520), (35.230, 31.600), (35.330, 32.330), (35.110, 31.450)]
data["spots"] = [P(*s) for s in SPOTS]
print("wb bounds", [round(v, 1) for v in data["wb_bounds"]], "centroid", data["wb_c"])
pickle.dump(data, open("geo/map.pkl", "wb"))
