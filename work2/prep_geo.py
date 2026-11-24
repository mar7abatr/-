import json, pickle, math, os
import shapely
from shapely.geometry import shape, box, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
LAT0, LON0 = 31.95, 35.25
KX = math.cos(math.radians(LAT0)) * 111.32
KY = 110.57

def P(lon, lat): return ((lon - LON0) * KX, -(lat - LAT0) * KY)
def proj(g): return shapely.transform(g, lambda c: [P(x, y) for x, y in c])

def polys(g):
    return [g] if isinstance(g, Polygon) else [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon)]

def rings(g, tol):
    g = proj(g).simplify(tol)
    return [[list(p.exterior.coords)] + [list(r.coords) for r in p.interiors] for p in polys(g) if not p.is_empty and p.area > 0.01]

d = json.load(open(f"{HERE}/geo/oslo.geojson"))
by = {}
for f in d["features"]:
    by[f["properties"]["class"]] = shape(f["geometry"]).buffer(0)
for k, g in by.items(): print(k, round(proj(g).area, 1), "km2")
A = by["AREA (A)"]; B = by["AREA (B)"]
allwb = unary_union(list(by.values())).buffer(0.0008).buffer(-0.0008)
ej = by["Israeli Declared East Jerusalem"]
C = allwb.difference(A).difference(B).difference(ej)
tot = proj(allwb).area
print("share A %.1f B %.1f C %.1f" % tuple(100 * proj(g).area / tot for g in (A, B, C)))

REG = box(33.5, 30.3, 37.2, 33.6)
ne = json.load(open(f"{HERE}/../work/geo/ne_countries.geojson"))
cs = [shape(f["geometry"]).buffer(0).intersection(REG) for f in ne["features"]
      if f["properties"].get("ADMIN") in ("Israel", "Egypt", "Jordan", "Palestine", "Lebanon", "Syria", "Saudi Arabia")]
land = unary_union([g for g in cs if not g.is_empty] + [allwb])
borders = []
for g in cs:
    if g.is_empty: continue
    b = proj(g.boundary).simplify(0.3)
    for ln in getattr(b, "geoms", [b]):
        c = list(ln.coords)
        if len(c) > 1: borders.append(c)

# illustrative attack markers: inside Area A polygons (largest first) plus some in B/C
apolys = sorted(polys(A), key=lambda p: -p.area)
spotsA = [P(*p.representative_point().coords[0]) for p in apolys[:9]]
bc = sorted(polys(B), key=lambda p: -p.area)[:4] + sorted(polys(C), key=lambda p: -p.area)[:3]
spotsO = [P(*p.representative_point().coords[0]) for p in bc]

data = dict(land=rings(land, 0.4), borders=borders, wb=rings(allwb, 0.08),
            A=rings(A, 0.05), B=rings(B, 0.05), C=rings(C, 0.06), EJ=rings(ej, 0.05),
            spotsA=spotsA, spotsO=spotsO, bounds=proj(allwb).bounds, c=proj(allwb).centroid.coords[0],
            repB=P(*sorted(polys(B), key=lambda p: -p.area)[0].representative_point().coords[0]),
            repC=P(*C.buffer(-0.01).representative_point().coords[0]))
print("bounds", [round(v, 1) for v in data["bounds"]], "rings A/B/C", len(data["A"]), len(data["B"]), len(data["C"]))
pickle.dump(data, open(f"{HERE}/geo/map.pkl", "wb"))
