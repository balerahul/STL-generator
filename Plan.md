# Project Plan (v2): Rectangular STL Grid Generator — Zero‑Thickness with Center Hole

## 0) One‑Line Summary

Create a base axis‑aligned rectangular **surface** oriented to X, Y, or Z; split it into an `nx × ny` grid; for each cell export two **zero‑thickness** STL meshes: (1) the **outer** rectangle, and (2) the **outer rectangle with a concentric inner rectangular hole** sized by `sx, sy`.

---

## 1) Problem Statement & Scope

* Build planar rectangular meshes with plane normal along `±X`, `±Y`, or `±Z`.
* Subdivide the rectangle into `nx × ny` cells in local in‑plane coordinates `(u, v)`.
* For each cell `(i, j)`, emit **two STL files** (no extrusion):

  1. **Outer**: the full cell rectangle triangulated (2 triangles).
  2. **Ring**: the cell rectangle with a **centered rectangular hole** matching the inner concentric rectangle.
* Deliverables: Python package + CLI that writes `2 × nx × ny` STL files.

> Note: Zero‑thickness STL (non‑manifold surface) is intentional; many CAD/CAM pipelines accept it for templates, outlines, laser paths, and sketch imports.

---

## 2) Inputs (CLI & API)

**Required:**

* `nx, ny` (int ≥ 1): grid counts along local axes `(u, v)`.
* `W, H` (float > 0): total rectangle size in local `(u, v)` units.
* `orientation` (str): one of `x|y|z` → plane normal is +X, +Y, +Z. Optional `normal_sign` ∈ {+1, −1}, default `+1`.

**Inner rectangle (hole) size:**

* `sx, sy` (float > 0): inner size per cell.
* `inner_size_mode` ∈ {`relative`, `absolute`}:

  * `relative` (default): `sx, sy` are **fractions** of the cell size in `u` and `v` (0 < sx ≤ 1, 0 < sy ≤ 1).
  * `absolute`: `sx, sy` are **lengths** in same units as `W, H`.

**Placement & rotation:**

* `origin = (cx, cy, cz)` (float3): world center of the whole rectangle. Default `(0, 0, 0)`.
* `rotate_deg` (float): in‑plane rotation about the plane normal, applied to `(û, ṽ)`. Default `0`.

**Output & formatting:**

* `out_dir` (path)
* `cell_filename_outer` pattern (default `cell_{i}_{j}_outer.stl`)
* `cell_filename_ring`  pattern (default `cell_{i}_{j}_ring.stl`)
* `stl_ascii` (bool): ASCII if true, else binary (default False)

**Optional niceties:**

* `border_gap` (float ≥ 0): shrink each **outer cell** bounds inward before defining the hole. Default `0`.

---

## 3) Outputs

* Exactly `2 × nx × ny` STL files:

  * `outer`: a 2‑triangle rectangle.
  * `ring`: a polygon‑with‑hole (outer rectangle minus inner rectangle) triangulated into a fan of triangles.
* Filenames encode cell indices `i, j` and type `{outer, ring}`.

---

## 4) Coordinate Frames & Mapping

Define orthonormal basis `(û, ṽ, ŵ)`:

* `ŵ` = plane normal from `orientation` and `normal_sign`.
* `(û, ṽ)` span the plane; for `z`: `û=(1,0,0)`, `ṽ=(0,1,0)`; for `x`: `û=(0,1,0)`, `ṽ=(0,0,1)`; for `y`: `û=(1,0,0)`, `ṽ=(0,0,1)`.
* Apply optional in‑plane rotation `rotate_deg` about `ŵ` to `(û, ṽ)`.

**World mapping (surface points):** for local `(u, v)`

```
P = origin + u*û + v*ṽ
```

---

## 5) Geometry Construction

### 5.1 Base rectangle & grid

* Extents: `u ∈ [-W/2, +W/2]`, `v ∈ [-H/2, +H/2]`.
* Cell sizes: `du = W/nx`, `dv = H/ny`.
* Cell `(i, j)` bounds:

  * `u0 = -W/2 + i*du`, `u1 = u0 + du`
  * `v0 = -H/2 + j*dv`, `v1 = v0 + dv`
* With `border_gap`:

  * `u0' = u0 + g`, `u1' = u1 - g`; `v0' = v0 + g`, `v1' = v1 - g`; ensure `u1' > u0'`, `v1' > v0'`.

### 5.2 Inner rectangle sizing

* Cell center `(uc, vc) = ((u0'+u1')/2, (v0'+v1')/2)`.
* Outer half‑sizes: `hu = (u1' - u0')/2`, `hv = (v1' - v0')/2`.
* Inner half‑sizes `(hiu, hiv)`:

  * Relative: `hiu = hu*sx`, `hiv = hv*sy`.
  * Absolute: `hiu = sx/2`, `hiv = sy/2`.
* Clamp: `0 < hiu ≤ hu`, `0 < hiv ≤ hv`.

### 5.3 Polygons

* **Outer rect (CCW)** around `(uc, vc)` and `(hu, hv)`.
* **Inner rect (CCW)** around `(uc, vc)` and `(hiu, hiv)`, later reversed to CW when building the polygon‑with‑hole for triangulation.

### 5.4 Triangulation (Zero‑Thickness)

* **Outer**: two triangles `(0,1,2)` and `(0,2,3)` from the outer rectangle CCW loop.
* **Ring**: triangulate polygon with **one hole** using `mapbox_earcut` (preferred) or `trimesh.triangulate_polygon` (Shapely backend). Ensure outer boundary CCW and hole boundary CW in local `(u, v)`.
* Map vertices to world with basis `(û, ṽ, ŵ)` and `origin`.

