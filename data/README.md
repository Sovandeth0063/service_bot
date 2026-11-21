# Demo Data — Sangkat Tonle Basak (`120101`)

Demo commune: **សង្កាត់ទន្លេបាសាក់ (Tonle Basak), ខណ្ឌចំការមន (Chamkar Mon), រាជធានីភ្នំពេញ** — 16 villages (ភូមិ ១–១៦).

Chosen because it is the example code already used in the PRD/architecture, it is urban (សង្កាត់) with many hospitals and services within 4 km, and DataEF has a coordinate reference point for it.

> ⚠️ **Demo data only.** Nothing here has been test-called or confirmed by the sangkat. Rows carry a `verification_status`; the bot should render `missing` phones as "កំពុងផ្ទៀងផ្ទាត់" rather than hiding the place.

---

## Folder layout

```
data/
├── raw/                      # untouched downloads (re-downloadable)
│   ├── dataef/               # data.mef.gov.kh
│   └── osm/                  # OpenStreetMap Overpass export
└── seed/                     # curated files the bot loads
```

## Raw sources (downloaded 2026-11-21)

### DataEF — `https://data.mef.gov.kh/api/v1/public-datasets/<id>/file`

| File | Dataset ID | Rows | Used for |
| :--- | :--- | ---: | :--- |
| `provinces_2025.csv` | `pd_66a8603700604c000123e144` | 25 | `provinces` table |
| `districts_2025.csv` | `pd_66a8603800604c000123e145` | 210 | `districts` table |
| `communes_2025.csv` | `pd_66a8603900604c000123e146` | 1,661 | `communes` table, code validation |
| `villages_2025.csv` | `pd_66a8603a00604c000123e147` | 14,576 | demo village list (Phase 2 table) |
| `geographical_list_2025.csv` | `pd_68e370856a965e00074a5e7b` | 14,576 | Flat join of all 4 levels (convenient single-file ETL) |
| `phnom_penh_coordinates.csv` | `pd_66ab60fbbcc3db0001df670f` | — | Sangkat/village reference points; **only source with a `Type` column (Khan/Sangkat/Village)** |
| `commune_boundaries.geojson` | `pd_66c2f89949eb6c00013c1385` | 1,633 | Phase 2 GPS binding |
| `public_hospitals_by_province_2022.csv` | `pd_6768d9b031140500019758c4` | 25 | Context only (aggregates, no facility list) |
| `public_health_centers_by_province.csv` | `pd_677655df93d4f00001fc5779` | 25 | Context only (counts per province) |
| `population_by_commune_2019.csv` | `pd_6706036740cc5500017936c0` | few | Context only (Boeng Keng Kang only) |

The API also offers paged JSON: `/api/v1/public-datasets/<id>/json?page=1` and a catalog at `/api/v1/public-datasets?page=1&page_size=100` (1,070 datasets).

**ETL gotchas found:**
* All DataEF admin CSVs start with a UTF-8 BOM → read with `encoding="utf-8-sig"`, or the first header becomes `﻿province_code`.
* Codes are zero-padded strings (`01`, `0102`, `010201`) → never parse as integers.
* **No `commune_type` (ឃុំ/សង្កាត់) column** in the 2025 lists. For the demo it is set by hand. For more communes: all of Phnom Penh (`12xxxx`) is សង្កាត់; elsewhere you need the district type (ក្រុង → សង្កាត់, ស្រុក → ឃុំ), which these CSVs don't include.
* **Boundary GeoJSON is the 2018 edition** (`khm_admbnda_adm3_gov_20181004`, codes prefixed `KH`). **117 of the 1,661 2025 communes have no polygon**, and 89 polygons use codes no longer in the 2025 list. GPS binding (Phase 2) needs a newer boundary file or a code-mapping table.
* DataEF has **no facility-level data** (no hospital/police/fire names, phones or locations) — only provincial aggregates.

### OpenStreetMap — `raw/osm/osm_tonle_basak_pois.json`

Overpass query around the sangkat reference point (11.5504, 104.9314): hospitals/clinics (4.5 km), police/fire/townhall (5 km), government offices (2.5 km). © OpenStreetMap contributors, ODbL — attribution required if shown publicly.

OSM gave good **names (Khmer + English) and coordinates** but almost **no phone numbers** for public facilities, and **no** Tonle Basak sangkat hall, administrative police post, or health center.

### Web sources for phone numbers
See the `source` / `source_ref` columns in each seed file (UK FCDO, Australian/German/Canadian embassy lists, Phnom Penh Post, expat.com).

---

## Seed files

| File | Rows | Maps to table | Status |
| :--- | ---: | :--- | :--- |
| `demo_commune.csv` | 1 | `communes` (subset) | ✅ From DataEF |
| `demo_villages.csv` | 16 | `villages` (subset) | ✅ From DataEF |
| `commune_configs.csv` | 1 | `commune_configs` | ⚠️ Hall phone/pin/hours are placeholders |
| `national_emergency_numbers.csv` | 5 | new `emergency_numbers` (or `local_contacts` with `commune_code` NULL) | ⚠️ 117/118/119/666 published by several sources, not test-called; 115 inactive (unconfirmed) |
| `local_contacts.csv` | 10 | `local_contacts` | ⚠️ 2 phones from published lists (1 conflicting), 1 fire phone published; rest `missing` |
| `public_services.csv` | 3 | `public_services` | ⚠️ Draft text; fees/times blank — clerk must confirm |
| `demo_announcements.csv` | 4 | `announcements` | Demo (one already expired, to test the expiry filter) |
| `keywords_kh.csv` | 37 | keyword matcher | Draft |
| `bot_copy_kh.json` | — | UI strings | Draft — native-speaker review needed |

Multi-value fields (`phone_numbers`, `required_docs_kh`) use ` | ` as the separator.

### `verification_status` values
| Value | Meaning | Bot behaviour |
| :--- | :--- | :--- |
| `verified` | Test-called / confirmed by the sangkat, with date | Show normally |
| `unverified_published` | Found in a published source, not yet called | Show (demo OK; must become `verified` before a real pilot) |
| `conflicting` | Sources disagree | Show first value; fix before pilot |
| `missing` | Not found | Show place + map, phone as "កំពុងផ្ទៀងផ្ទាត់" |
| `draft_needs_clerk` | Written by us, not confirmed | Demo only |

---

## Gaps to fill (in priority order)

1. **Tonle Basak administrative police post** — name, phone, location (also needed for the residence/family book guide).
2. **Sangkat hall** — real phone, exact map pin, office hours.
3. **Health center** serving Tonle Basak.
4. **Phones** for Preah Ang Duong, Phnom Penh Municipal, Kantha Bopha, Koh Pich fire, Chamkar Mon police.
5. **Resolve** Khmer-Soviet Hospital's number (023 217 524 / 217 384 / 217 764).
6. **Fees and processing times** for the 3 service guides.
7. Test-call every number from a Cambodian SIM and set `verification_status=verified`.
