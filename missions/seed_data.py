"""
Seed metadata used by the data migration and by `import_missions`.

Nothing here is required at runtime: every value ends up in the database and can be
edited from /admin/. Add new missions in the admin (or here) without touching code.
"""

CATEGORY_META = {
    'mars': {
        'name': 'Mars', 'kind': 'planetary', 'icon': '🔴', 'order': 1,
        'description': 'Landers and rovers that searched the Red Planet for water and signs of ancient life.',
        'texture_image': 'images/planets/mars-texture.jpg',
    },
    'moon': {
        'name': 'Moon', 'kind': 'planetary', 'icon': '🌕', 'order': 2,
        'description': "Humanity's first destination beyond Earth, walked by Apollo astronauts.",
        'texture_image': 'images/planets/moon-texture.jpg',
    },
    'space': {
        'name': 'Space', 'kind': 'deep_space', 'icon': '🛰️', 'order': 3,
        'description': 'Observatories and probes working in solar orbit, at Lagrange points and in interstellar space. No planetary surfaces here.',
        'texture_image': 'images/planets/space-texture.jpg',
    },
}

# Keyed by Vehicle.id as shipped in data.json (used only to initialise existing rows).
VEHICLE_META = {
    1: {'slug': 'opportunity-rover', 'tagline': 'Built for 90 days. Explored for 14 years.',
        'mission_type': 'Mars rover', 'status_label': 'Mission complete (2019)',
        'specs': [('Launch mass', '185 kg'), ('Power', 'Solar arrays'), ('Planned lifetime', '90 sols'),
                  ('Actual lifetime', '5,111 sols (14+ years)'), ('Distance driven', '45.16 km')]},
    2: {'slug': 'viking-1-lander', 'tagline': 'The first long-lived robotic station on Mars.',
        'mission_type': 'Mars lander', 'status_label': 'Mission complete (1982)',
        'specs': [('Power', '2 radioisotope generators (RTG)'), ('Landing site', 'Chryse Planitia'),
                  ('Operated', 'More than 6 years'), ('Contact lost', 'November 1982')]},
    3: {'slug': 'apollo-11-eagle', 'tagline': 'One small step, one giant leap.',
        'mission_type': 'Crewed lunar module', 'status_label': 'Mission complete (1969)',
        'specs': [('Crew on surface', '2 (Armstrong, Aldrin)'), ('Landing site', 'Sea of Tranquility'),
                  ('Time on surface', '21 h 36 min'), ('Moonwalk', 'About 2 h 31 min'), ('Samples returned', '21.5 kg')]},
    4: {'slug': 'apollo-15-falcon', 'tagline': 'The first mission to drive on the Moon.',
        'mission_type': 'Crewed lunar module', 'status_label': 'Mission complete (1971)',
        'specs': [('Crew on surface', '2 (Scott, Irwin)'), ('Landing site', 'Hadley–Apennine'),
                  ('Time on surface', 'About 67 hours'), ('Lunar Rover distance', '27.9 km'), ('Samples returned', '77 kg')]},
    5: {'slug': 'mars-pathfinder', 'tagline': 'Proof that faster, better, cheaper could work.',
        'mission_type': 'Lander + microrover', 'status_label': 'Mission complete (1997)',
        'specs': [('Rover', 'Sojourner (10.5 kg)'), ('Landing method', 'Airbag-cushioned'),
                  ('Designed lifetime', '7–30 days'), ('Operated', 'About 83 days')]},
    6: {'slug': 'spirit-rover', 'tagline': "Oppy's twin and the rover that found ancient hot springs.",
        'mission_type': 'Mars rover', 'status_label': 'Mission complete (2011)',
        'specs': [('Launch mass', '185 kg'), ('Landing site', 'Gusev Crater'), ('Distance driven', '7.73 km'),
                  ('Last contact', 'March 2010')]},
    7: {'slug': 'james-webb-space-telescope', 'tagline': "Humanity's infrared eye on the early universe.",
        'mission_type': 'Space observatory', 'status_label': 'Operating',
        'milestone_label': 'Arrived at L2', 'location_label': 'Position',
        'specs': [('Orbit', 'Halo orbit around Sun–Earth L2'), ('Primary mirror', '6.5 m, 18 gold-coated segments'),
                  ('Wavelengths', '0.6–28.5 micrometres (infrared)'), ('Operating temperature', 'Below 50 K (−223 °C)'),
                  ('Launch vehicle', 'Ariane 5'), ('Partners', 'NASA, ESA, CSA')]},
    8: {'slug': 'voyager-1', 'tagline': "Humanity's farthest emissary, now in interstellar space.",
        'mission_type': 'Interstellar probe', 'status_label': 'Operating',
        'milestone_label': 'Entered interstellar space', 'location_label': 'Position',
        'specs': [('Launch mass', '825.5 kg'), ('Power', '3 radioisotope generators (RTG)'),
                  ('Speed', 'About 17 km/s relative to the Sun'), ('Message', 'The Golden Record')],
        'story': ("I am Voyager 1, humanity's farthest emissary in the cosmos. Launched in 1977 on a grand tour of the outer "
                  "solar system, I have been traveling outward ever since, powered by three radioisotope generators and carrying "
                  "instruments that sniff the charged particles and magnetic fields of space itself. In 1990, at the request of "
                  "astronomer Carl Sagan, I turned my camera back toward home one final time to capture the 'Pale Blue Dot'—Earth "
                  "appearing as a tiny speck of dust suspended in a sunbeam. On August 25, 2012, I crossed the heliopause, the edge "
                  "of the Sun's bubble of solar wind, and became the first human-made object to enter interstellar space. Bolted to "
                  "my chassis is the Golden Record: a gold-plated copper phonograph containing greetings in 55 languages, sounds of "
                  "thunder and birds, and music from Earth, voyaging forever across the Milky Way.")},
    9: {'slug': 'parker-solar-probe', 'tagline': 'The mission to touch the Sun.',
        'mission_type': 'Solar probe', 'status_label': 'Operating',
        'milestone_label': 'Entered the solar corona', 'location_label': 'Position',
        'specs': [('Launch mass', 'About 685 kg'), ('Closest approach', '6.1 million km from the Sun (Dec 2024)'),
                  ('Top speed', 'About 692,000 km/h'), ('Heat shield', 'Carbon-composite, about 1,400 °C at the front'),
                  ('Orbit', 'Highly elliptical solar orbit')]},
}
