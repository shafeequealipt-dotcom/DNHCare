"""Local-SEO location data — the ONE place Varthur and the ~10 km service area are
defined. Imported by the prompt builder, the HTML template, the GBP blurb and the
safety gate (agent/check_post.py) so they can never drift apart.

Dependency-free on purpose: check_post.py runs as a plain script and must be able
to import this without the bot package or any env vars.

To change the service area, edit NEARBY_AREAS below (closest first). The list is
approximate neighbourhoods within roughly 10 km of Varthur — not a measured survey.
"""

PRIMARY = "Varthur"
CITY = "Bengaluru"
RADIUS_KM = 10

# Clinic coordinates (same values as the site-wide MedicalClinic schema in index.html).
CENTER_LAT = 12.9350
CENTER_LNG = 77.7450

# Neighbourhoods / roads within roughly 10 km of Varthur, closest first.
NEARBY_AREAS = [
    "Gunjur",
    "Balagere",
    "Thubarahalli",
    "Siddapura",
    "Hagadur",
    "Whitefield",
    "Panathur",
    "Kadubeesanahalli",
    "Carmelaram",
    "Bellandur",
    "Brookefield",
    "Marathahalli",
    "Sarjapur Road",
    "Kadugodi",
    "Dommasandra",
]

# The gate fails a post that mentions fewer than this many distinct nearby areas.
# (The template always lists every area, so a healthy post carries all of them.)
MIN_AREAS_IN_POST = 5
