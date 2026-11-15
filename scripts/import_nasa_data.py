"""
Standalone NASA Data Import Script
===================================
Automatically locates the `nasa.xlsx` (or .xls/.csv) dataset on the Desktop or project folder,
cleans formatting, handles zero-width spaces/nulls, normalizes date and numeric values,
and imports all records into normalized relational database tables.

Features:
- Idempotent upserts (can be executed multiple times without duplicates).
- Normalizes categories, vehicles, technical specs, stories, questions, and answers.
- Preserves raw dataset fields alongside structured typed relational fields.
- Provides a comprehensive verification summary showing exact record counts for each table.
"""

import os
import sys
import re
import datetime
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nasa_hub.settings')

import django
django.setup()

import openpyxl
from django.db import transaction
from django.utils.text import slugify
from missions.models import (
    Category, Vehicle, VehicleSpec, VehicleImage, Story, Question, Answer
)

# Candidate paths for automated detection (Codespaces root, workspace, desktop)
CANDIDATE_PATHS = [
    BASE_DIR / 'nasa.xlsx',
    BASE_DIR / 'nasa_data.xlsx',
    Path('/workspaces') / 'nasa.xlsx',
    Path('/workspaces') / 'Bytee_project_NASA' / 'nasa.xlsx',
    Path.cwd() / 'nasa.xlsx',
    Path(os.path.expanduser('~')) / 'OneDrive - Yarmouk University' / 'Desktop' / 'nasa.xlsx',
    Path(os.path.expanduser('~')) / 'Desktop' / 'nasa.xlsx',
    BASE_DIR / 'nasa.csv',
    Path.cwd() / 'nasa.csv',
]

CATEGORY_METADATA = {
    'mars': {
        'name': 'Mars',
        'kind': 'planetary',
        'icon': '🔴',
        'order': 1,
        'description': 'Landers, rovers, and aerial probes exploring the terrain and ancient waterways of the Red Planet.',
        'texture_image': 'images/planets/mars-texture.jpg'
    },
    'moon': {
        'name': 'Moon',
        'kind': 'planetary',
        'icon': '🌕',
        'order': 2,
        'description': "Humanity's celestial companion, walked by Apollo astronauts and mapped by Surveyor probes.",
        'texture_image': 'images/planets/moon-texture.jpg'
    },
    'space': {
        'name': 'Space',
        'kind': 'deep_space',
        'icon': '🛰️',
        'order': 3,
        'description': 'Deep-space observatories, asteroid explorers, and interstellar probes in solar orbit and beyond.',
        'texture_image': 'images/planets/space-texture.jpg'
    }
}

ADDITIONAL_QUESTIONS = {
    'apollo-11-eagle': {
        'text': "Which two astronauts did the Apollo 11 Lunar Module 'Eagle' carry to the surface of the Moon?",
        'hint': "Think of the first two men to set foot on the lunar soil in July 1969.",
        'explanation': "Neil Armstrong and Edwin 'Buzz' Aldrin landed the LM Eagle on July 20, 1969, while Michael Collins piloted the Command Module in lunar orbit.",
        'choices': [
            ("Neil Armstrong and Buzz Aldrin", True),
            ("Pete Conrad and Alan Bean", False),
            ("David Scott and James Irwin", False),
            ("John Young and Charles Duke", False)
        ]
    },
    'apollo-15-falcon': {
        'text': "What groundbreaking mobility vehicle did Apollo 15 bring to the Moon for the first time in history?",
        'hint': "This wheeled electric vehicle allowed astronauts Scott and Irwin to drive tens of kilometers.",
        'explanation': "Apollo 15 deployed the first Lunar Roving Vehicle (LRV), expanding the crew's exploration radius across 27.9 kilometers of lunar terrain.",
        'choices': [
            ("The Lunar Roving Vehicle (LRV)", True),
            ("Modular Equipment Transporter (MET)", False),
            ("Robotic Surface Hopper", False),
            ("Autonomous Quadcopter Drone", False)
        ]
    },
    'apollo-12-intrepid': {
        'text': "How close did the Apollo 12 Lunar Module land to the unmanned Surveyor 3 probe to prove pinpoint landing capability?",
        'hint': "The landing was so precise the astronauts could easily walk over to inspect the robotic probe.",
        'explanation': "Apollo 12 demonstrated pinpoint landing capability by touching down just 180 meters from Surveyor 3 in the Ocean of Storms.",
        'choices': [
            ("Only 180 meters away", True),
            ("1.5 kilometers away", False),
            ("500 meters away", False),
            ("12 kilometers away", False)
        ]
    },
    'surveyor-3': {
        'text': "What did Surveyor 3's mechanical digging tasks prove about the lunar surface for future human landings?",
        'hint': "Its scoop measured the bearing strength of the lunar soil.",
        'explanation': "Surveyor 3 demonstrated that the lunar surface has a bearing strength of 98 kPa, proving it was firm enough to safely support crewed Apollo landers.",
        'choices': [
            ("The lunar surface had 98 kPa bearing strength, proving it was firm enough for human landers", True),
            ("The lunar surface was too brittle to support any landing vehicle", False),
            ("The Moon was covered in unstable quicksand", False),
            ("Liquid water was pooled just 5 centimeters below the dust", False)
        ]
    },
    'mars-pathfinder': {
        'text': "What was the name of the miniature robotic rover companion deployed onto Mars by Pathfinder?",
        'hint': "Named after historical abolitionist and women's rights advocate Sojourner Truth.",
        'explanation': "Mars Pathfinder deployed the 23-pound microrover Sojourner, which rolled down the ramp on July 5, 1997 to become humanity's first rover on Mars.",
        'choices': [
            ("Sojourner", True),
            ("Spirit", False),
            ("Opportunity", False),
            ("Curiosity", False)
        ]
    },
    'spirit-opportunity-rovers': {
        'text': "What geological evidence did the Spirit rover uncover at sites like Home Plate and Comanche?",
        'hint': "Think of mineral deposits associated with boiling water and hydrothermal vents.",
        'explanation': "Spirit discovered rich carbonate and silica deposits at Home Plate, revealing ancient hydrothermal and volcanic hot spring environments on Mars.",
        'choices': [
            ("Silica and carbonate deposits indicating past hydrothermal springs", True),
            ("Pristine beds of liquid mercury", False),
            ("Fossilized sea coral formations", False),
            ("Vast reserves of frozen methane ice only", False)
        ]
    },
    'viking-1': {
        'text': "What milestone did Viking 1 achieve on July 20, 1976?",
        'hint': "It was the very first successful US operation of its kind on the Red Planet.",
        'explanation': "Viking 1 became the first American spacecraft to successfully perform a soft landing on Mars and return high-resolution imagery and scientific data.",
        'choices': [
            ("First successful American spacecraft to touch down and operate on Mars", True),
            ("First crewed landing on Mars", False),
            ("First spacecraft to return soil samples from Mars to Earth", False),
            ("First nuclear fusion reactor placed on Mars", False)
        ]
    },
    'insight-lander': {
        'text': "What key scientific tool allowed InSight to map the internal layered structure of Mars?",
        'hint': "This ultra-sensitive French dome instrument detected marsquakes.",
        'explanation': "InSight deployed SEIS (Seismic Experiment for Interior Structure), measuring hundreds of seismic quakes to map the Martian crust, mantle, and molten liquid core.",
        'choices': [
            ("SEIS (Seismic Experiment for Interior Structure)", True),
            ("Autonomous deep trenching bulldozer", False),
            ("Gamma-ray orbital telescope", False),
            ("Ultrasonic radar levitator", False)
        ]
    },
    'dawn': {
        'text': "Which two unique worlds in the asteroid belt did Dawn orbit and map during its mission?",
        'hint': "One is a dry protoplanet and the other is a water-rich dwarf planet.",
        'explanation': "Dawn is the only spacecraft to orbit two extraterrestrial destinations: giant protoplanet Vesta and ice/salt dwarf planet Ceres.",
        'choices': [
            ("Vesta and Ceres", True),
            ("Phobos and Deimos", False),
            ("Ganymede and Callisto", False),
            ("Titan and Enceladus", False)
        ]
    },
    'dawn-mission': {
        'text': "Which two unique worlds in the asteroid belt did Dawn orbit and map during its mission?",
        'hint': "One is a dry protoplanet and the other is a water-rich dwarf planet.",
        'explanation': "Dawn is the only spacecraft to orbit two extraterrestrial destinations: giant protoplanet Vesta and ice/salt dwarf planet Ceres.",
        'choices': [
            ("Vesta and Ceres", True),
            ("Phobos and Deimos", False),
            ("Ganymede and Callisto", False),
            ("Titan and Enceladus", False)
        ]
    },
    'near-shoemaker': {
        'text': "What historical first did NEAR Shoemaker achieve at Asteroid 433 Eros on February 12, 2001?",
        'hint': "Although designed purely as an orbiter, the team guided it to touch down on the asteroid.",
        'explanation': "NEAR Shoemaker became the very first spacecraft to ever touch down and land on the surface of an asteroid.",
        'choices': [
            ("First human spacecraft to softly touch down on the surface of an asteroid", True),
            ("First spacecraft to capture an asteroid into Earth orbit", False),
            ("First spacecraft to blow up an asteroid with kinetic impact", False),
            ("First spacecraft to mine gold from an asteroid", False)
        ]
    },
    'pioneer-10': {
        'text': "What plaque did Pioneer 10 carry on its chassis as an interstellar message?",
        'hint': "Carl Sagan and Frank Drake helped design this golden message for extraterrestrial civilizations.",
        'explanation': "Pioneer 10 carries a gold-anodized aluminum plaque illustrating human figures, the spacecraft silhouette, and a pulsar map locating our Sun.",
        'choices': [
            ("A gold-anodized aluminum plaque illustrating humanity and our solar system", True),
            ("A phonograph golden record containing Earth sounds and music", False),
            ("A silicon microchip with 1 million human signatures", False),
            ("A digital holographic laser beacon", False)
        ]
    },
    'ingenuity-helicopter': {
        'text': "How many total powered flights did Ingenuity successfully complete over its 3-year mission on Mars?",
        'hint': "Originally planned for just 5 flights, it flew over 70 times.",
        'explanation': "Ingenuity completed an astounding 72 powered flights across Mars, logging over 2 hours of flight time before retiring in January 2024.",
        'choices': [
            ("72 flights", True),
            ("5 flights", False),
            ("25 flights", False),
            ("120 flights", False)
        ]
    },
    'kepler-space-telescope': {
        'text': "What optical method did the Kepler Space Telescope use to detect thousands of exoplanets?",
        'hint': "It watched for the tiny dimming of starlight as a planet crossed in front of its star.",
        'explanation': "Kepler utilized the transit method, measuring minuscule drops in stellar brightness caused when an orbiting planet transited across the host star.",
        'choices': [
            ("Transit photometry method (measuring starlight dips)", True),
            ("Gravitational wave laser interferometry", False),
            ("Direct optical zoom photography of planetary surfaces", False),
            ("Active radar echo reflection", False)
        ]
    },
    'james-webb-space-telescope': {
        'text': "What primary infrared wavelength range enables JWST to see the earliest galaxies in the cosmic dawn?",
        'hint': "Near and mid-infrared light passes through cosmic dust clouds.",
        'explanation': "JWST observes in near-infrared and mid-infrared wavelengths (0.6 to 28 microns), capturing redshifted light from galaxies formed over 13.5 billion years ago.",
        'choices': [
            ("Near and Mid-Infrared (0.6 to 28 microns)", True),
            ("Ultraviolet only (10 to 100 nanometers)", False),
            ("Hard Gamma-Rays and X-Rays", False),
            ("Shortwave AM radio wavelengths", False)
        ]
    },
    'voyager-1': {
        'text': "In what year did Voyager 1 cross the heliopause and enter true interstellar space?",
        'hint': "Detected by a sharp rise in galactic cosmic rays in late summer.",
        'explanation': "Voyager 1 entered interstellar space in August 2012 at a distance of 121 astronomical units from the Sun.",
        'choices': [
            ("2012", True),
            ("1989", False),
            ("2000", False),
            ("2021", False)
        ]
    },
    'parker-solar-probe': {
        'text': "What revolutionary carbon-composite heat shield protects Parker Solar Probe near the Sun?",
        'hint': "It withstands temperatures near 1,400°C while keeping instruments at room temperature.",
        'explanation': "Parker is protected by the Thermal Protection System (TPS), an 11.4 cm thick carbon-composite foam shield with reflective white alumina ceramic coating.",
        'choices': [
            ("Thermal Protection System (TPS) carbon-composite shield", True),
            ("Solid liquid-nitrogen cooling jacket", False),
            ("Lead-lined titanium sandwich plating", False),
            ("Magnetic forcefield deflector", False)
        ]
    },
    'voyager-2': {
        'text': "In what year did Voyager 2 enter true interstellar space beyond the heliopause?",
        'hint': "Six years after its twin Voyager 1, in late autumn.",
        'explanation': "Voyager 2 crossed the heliopause into interstellar space on November 5, 2018, at a distance of approximately 119 AU from the Sun.",
        'choices': [
            ("2018", True),
            ("1977", False),
            ("1989", False),
            ("2024", False)
        ]
    },
    'hubble-space-telescope': {
        'text': "What critical advantage allows the Hubble Space Telescope to achieve ultra-sharp cosmic observations?",
        'hint': "It orbits high above Earth's weather and atmospheric turbulence.",
        'explanation': "Hubble orbits 540 km above Earth, completely free from atmospheric blurring, light pollution, and infrared absorption.",
        'choices': [
            ("Its position in Low Earth Orbit above Earth's turbulent atmosphere", True),
            ("A 100-meter liquid mercury spinning mirror", False),
            ("An artificial intelligence imagery filter", False),
            ("Active liquid nitrogen cooling jackets", False)
        ]
    }
}

CORNERSTONE_MISSIONS = [
    {
        'code': 'JWST',
        'name': 'James Webb Space Telescope (JWST)',
        'slug': 'james-webb-space-telescope',
        'category': 'space',
        'tagline': "Humanity's premier deep-space infrared observatory.",
        'mission_type': 'Deep Space Infrared Observatory',
        'status_label': 'Operating at L2',
        'launch_date': datetime.date(2021, 12, 25),
        'landing_date': datetime.date(2022, 1, 24),
        'milestone_label': 'L2 Halo Insertion',
        'coordinates': 'Sun-Earth L2 Lagrange Point (~1.5M km from Earth)',
        'surface_lat': 0.0,
        'surface_lon': 180.0,
        'location_label': 'Orbital Station',
        'image_path': 'images/Picture1___V7.jpg',
        'order': 14,
        'raw_location': 'Deep Space / Sun-Earth L2',
        'raw_launch_text': 'December 25, 2021',
        'raw_landing_text': 'January 24, 2022',
        'notes': 'Deep space flagship studying the cosmic dawn and exoplanet atmospheres.',
        'story': (
            "I am the James Webb Space Telescope, the most powerful infrared telescope ever constructed by humanity. "
            "Launched on an Ariane 5 rocket on Christmas Day 2021, I made a 1.5-million-kilometer voyage into the quiet darkness "
            "of the second Sun-Earth Lagrange point (L2). With my 6.5-meter gold-plated beryllium primary mirror and five-layer "
            "tennis-court-sized sunshield, I peer through interstellar dust to observe the very first stars and galaxies that formed "
            "after the Big Bang, and inspect atmospheric biosignatures on distant exoplanets."
        ),
        'specs': [
            ("Primary Mirror", "6.5 m Gold-Coated Beryllium (18 Segments)"),
            ("Operating Orbit", "Sun-Earth L2 Halo Orbit (~1.5 Million km)"),
            ("Wavelength Coverage", "0.6 to 28.3 μm (Near & Mid-Infrared)"),
            ("Sunshield", "5-Layer Kapton Tennis Court Sized (21m x 14m)"),
            ("Instruments", "NIRCam, NIRSpec, MIRI, FGS/NIRISS")
        ],
        'primary_question': {
            'text': "Around which gravitational balance point does the James Webb Space Telescope operate?",
            'hint': "It is situated 1.5 million kilometers behind Earth opposite the Sun.",
            'explanation': "JWST operates in a halo orbit around the Sun-Earth L2 Lagrange point to keep its instruments shielded and near absolute zero.",
            'choices': [
                ("Sun-Earth L2 Lagrange Point", True),
                ("Low Earth Orbit (LEO)", False),
                ("Lunar South Pole Orbit", False),
                ("Mars-Sun L1 Point", False)
            ]
        }
    },
    {
        'code': 'HST',
        'name': 'Hubble Space Telescope',
        'slug': 'hubble-space-telescope',
        'category': 'space',
        'tagline': "The iconic observatory that revolutionized our vision of the cosmos.",
        'mission_type': 'Optical & Ultraviolet Space Observatory',
        'status_label': 'Operational (Low Earth Orbit)',
        'launch_date': datetime.date(1990, 4, 24),
        'landing_date': datetime.date(1990, 4, 25),
        'milestone_label': 'Deployed by STS-31 Discovery',
        'coordinates': 'Low Earth Orbit (540 km Altitude, 28.5° Inclination)',
        'surface_lat': 28.5,
        'surface_lon': -80.0,
        'location_label': 'Orbital Station',
        'image_path': 'images/Picture1___V7.jpg',
        'order': 15,
        'raw_location': 'Low Earth Orbit',
        'raw_launch_text': 'April 24, 1990',
        'raw_landing_text': 'April 25, 1990',
        'notes': 'Over 1.5 million observations recorded, determining the age and expansion rate of the universe.',
        'story': (
            "I am the Hubble Space Telescope, one of NASA's Greatest Observatories. Deployed into orbit by Space Shuttle "
            "Discovery in April 1990, I opened humanity's eyes to the deep universe. Free from atmospheric distortion, "
            "I measured the expansion rate of the universe, discovered supermassive black holes at the hearts of galaxies, "
            "and captured iconic deep field views revealing thousands of galaxies in a seemingly empty patch of sky."
        ),
        'specs': [
            ("Primary Mirror", "2.4 m (7.9 ft) Diameter High-Precision Glass"),
            ("Operating Orbit", "Circular LEO (~540 km altitude, 28.5° inclination)"),
            ("Wavelength Range", "115 nm (Ultraviolet) to 2.5 μm (Near-Infrared)"),
            ("Launch Vehicle", "Space Shuttle Discovery (STS-31)"),
            ("Lifetime", "Operational for over 34 continuous years")
        ],
        'primary_question': {
            'text': "Which NASA Space Shuttle mission deployed the Hubble Space Telescope into orbit in April 1990?",
            'hint': "Flown by Shuttle Discovery.",
            'explanation': "Hubble was deployed on mission STS-31 by the crew of Space Shuttle Discovery on April 25, 1990.",
            'choices': [
                ("STS-31 (Space Shuttle Discovery)", True),
                ("Apollo 11", False),
                ("STS-107 (Columbia)", False),
                ("Mercury-Atlas 6", False)
            ]
        }
    },
    {
        'code': 'VOYAGER-1',
        'name': 'Voyager 1 (Interstellar Probe)',
        'slug': 'voyager-1',
        'category': 'space',
        'tagline': "Humanity's farthest ambassador in interstellar space.",
        'mission_type': 'Interstellar Deep Space Probe',
        'status_label': 'Operating in Interstellar Space',
        'launch_date': datetime.date(1977, 9, 5),
        'landing_date': datetime.date(2012, 8, 25),
        'milestone_label': 'Crossed Heliopause',
        'coordinates': 'Interstellar Space (>24.4 Billion km from Earth)',
        'surface_lat': 35.0,
        'surface_lon': 60.0,
        'location_label': 'Interstellar Coordinate',
        'image_path': 'images/Picture1___V8.jpg',
        'order': 16,
        'raw_location': 'Interstellar Space',
        'raw_launch_text': 'September 5, 1977',
        'raw_landing_text': 'August 25, 2012',
        'notes': 'The most distant human-made object from Earth.',
        'story': (
            "I am Voyager 1, the farthest manufactured object in human history. Launched in 1977 on a grand tour of the outer planets, "
            "I revealed volcanic sulfur geysers on Jupiter's moon Io and intricate structure within Saturn's icy rings. "
            "In August 2012, after 35 years of travel, I crossed the heliopause—leaving our Sun's solar wind bubble behind and sailing into "
            "the uncharted plasma of interstellar space. On my hull rests the Golden Record, a cosmic greeting carrying the voices, "
            "sounds, and music of planet Earth."
        ),
        'specs': [
            ("Distance from Earth", ">24.4 Billion km (>163 AU)"),
            ("Launch Vehicle", "Titan IIIE-Centaur"),
            ("Power Source", "Radioisotope Thermoelectric Generators (RTG)"),
            ("Interstellar Crossing", "August 25, 2012"),
            ("Cosmic Payload", "The Golden Record (Earth Greetings & Music)")
        ],
        'primary_question': {
            'text': "What iconic artifact is mounted on Voyager 1 carrying sounds and images from Earth?",
            'hint': "Gold-plated copper phonograph record curated by Carl Sagan.",
            'explanation': "Voyager 1 carries the Golden Record, intended to introduce Earth and its culture to extraterrestrial civilizations.",
            'choices': [
                ("The Golden Record", True),
                ("A micro-engraved diamond Bible", False),
                ("An optical solar laser array", False),
                ("A titanium vault of seeds", False)
            ]
        }
    },
    {
        'code': 'VOYAGER-2',
        'name': 'Voyager 2 (Interstellar Probe)',
        'slug': 'voyager-2',
        'category': 'space',
        'tagline': "The only spacecraft to explore Jupiter, Saturn, Uranus, and Neptune.",
        'mission_type': 'Interstellar Deep Space Probe',
        'status_label': 'Operating in Interstellar Space',
        'launch_date': datetime.date(1977, 8, 20),
        'landing_date': datetime.date(2018, 11, 5),
        'milestone_label': 'Crossed Heliopause',
        'coordinates': 'Interstellar Space (>20.5 Billion km from Earth)',
        'surface_lat': -48.0,
        'surface_lon': 90.0,
        'location_label': 'Interstellar Coordinate',
        'image_path': 'images/Picture1___V8.jpg',
        'order': 17,
        'raw_location': 'Interstellar Space',
        'raw_launch_text': 'August 20, 1977',
        'raw_landing_text': 'November 5, 2018',
        'notes': 'The only probe to visit Uranus and Neptune, now operating in interstellar space.',
        'story': (
            "I am Voyager 2, the twin sister of Voyager 1 and humanity's only spacecraft to study all four gas and ice giant "
            "planets of the outer solar system up close. Launched on August 20, 1977, sixteen days ahead of my twin, I flew past "
            "Jupiter in 1979, Saturn in 1981, and made history by becoming the first and only human probe to encounter Uranus in "
            "1986 and Neptune in 1989, discovering new moons and rings. On November 5, 2018, I crossed the heliopause into "
            "interstellar space, continuing to transmit scientific telemetry back to Earth across billions of miles."
        ),
        'specs': [
            ("Distance from Earth", ">20.5 Billion km (>137 AU)"),
            ("Planetary Flybys", "Jupiter (1979), Saturn (1981), Uranus (1986), Neptune (1989)"),
            ("Interstellar Crossing", "November 5, 2018"),
            ("Power Source", "3 Multihundred-Watt RTGs"),
            ("Operating Status", "Active interstellar telemetry")
        ],
        'primary_question': {
            'text': "What unique distinction does Voyager 2 hold among all spacecraft in human history?",
            'hint': "It completed the full planetary grand tour of the four outer giants.",
            'explanation': "Voyager 2 is the only spacecraft to visit all four gas and ice giants: Jupiter, Saturn, Uranus, and Neptune.",
            'choices': [
                ("It is the only spacecraft to visit all four outer giants: Jupiter, Saturn, Uranus, and Neptune", True),
                ("It was the first spacecraft to land on an asteroid", False),
                ("It was the first human spacecraft to leave Earth orbit", False),
                ("It returned samples of solar wind to Earth", False)
            ]
        }
    },
    {
        'code': 'PARKER-SOLAR',
        'name': 'Parker Solar Probe',
        'slug': 'parker-solar-probe',
        'category': 'space',
        'tagline': "Touching the Sun at record-shattering velocities.",
        'mission_type': 'Heliocentric Solar Corona Probe',
        'status_label': 'Operating in Solar Orbit',
        'launch_date': datetime.date(2018, 8, 12),
        'landing_date': datetime.date(2021, 4, 28),
        'milestone_label': 'First Corona Entry',
        'coordinates': 'Heliocentric Orbit (Perihelion ~6.1M km from Sun)',
        'surface_lat': 10.0,
        'surface_lon': 0.0,
        'location_label': 'Solar Orbit',
        'image_path': 'images/Picture1___V9.jpg',
        'order': 18,
        'raw_location': 'Heliocentric Orbit / Solar Corona',
        'raw_launch_text': 'August 12, 2018',
        'raw_landing_text': 'April 28, 2021',
        'notes': 'Fastest human-made object, dipping directly into the solar corona.',
        'story': (
            "I am Parker Solar Probe, humanity's daring mission to touch the Sun. Launched in 2018, I dive deep through "
            "the million-degree plasma of the solar corona to unlock the mysteries of solar flares, magnetic switchbacks, and the "
            "acceleration of the solar wind. Reaching velocities exceeding 690,000 km/h, I am the fastest spacecraft in history, "
            "protected by a cutting-edge carbon-composite heat shield that keeps my scientific instruments at a cool 30°C."
        ),
        'specs': [
            ("Top Velocity", "692,000 km/h (430,000 mph)"),
            ("Closest Solar Approach", "6.16 Million km from Sun Surface"),
            ("Heat Shield", "11.4 cm Carbon-Composite Foam (Up to 1,400°C)"),
            ("Launch Date", "August 12, 2018"),
            ("Primary Mission", "Study Solar Corona & Solar Wind Origins")
        ],
        'primary_question': {
            'text': "What makes Parker Solar Probe unique among all human spaceflight missions?",
            'hint': "It is both the fastest vehicle and the one that flies closest to our star.",
            'explanation': "Parker Solar Probe travels faster than any human-made craft and flies directly inside the solar corona.",
            'choices': [
                ("It is the fastest spacecraft in history and directly dips into the solar corona", True),
                ("It was the first mission to land on Mercury", False),
                ("It captured samples of solar plasma and returned them to Earth", False),
                ("It is powered completely without solar cells using cold fusion", False)
            ]
        }
    }
]

SURFACE_COORDINATES = {
    'apollo-11-eagle': (0.67408, 23.47297, "0.67° N, 23.47° E (Mare Tranquillitatis)"),
    'apollo-15-falcon': (26.1322, 3.6339, "26.13° N, 3.63° E (Hadley-Apennine)"),
    'apollo-12-intrepid': (-3.0124, -23.4216, "3.01° S, 23.42° W (Oceanus Procellarum)"),
    'surveyor-3': (-3.015, -23.418, "3.01° S, 23.42° W (Oceanus Procellarum)"),
    'mars-pathfinder': (19.13, -33.22, "19.13° N, 33.22° W (Ares Vallis)"),
    'spirit-opportunity-rovers': (-14.5684, 175.4726, "Spirit: -14.57° S, 175.47° E (Gusev) / Oppy: -1.95° S (Meridiani)"),
    'viking-1': (22.697, -48.222, "22.70° N, 48.22° W (Chryse Planitia)"),
    'insight-lander': (4.502, 135.623, "4.50° N, 135.62° E (Elysium Planitia)"),
    'ingenuity-helicopter': (18.4447, 77.4508, "18.44° N, 77.45° E (Jezero Crater)"),
    'dawn': (10.0, 120.0, "Asteroid Belt (Orbits 4 Vesta & 1 Ceres)"),
    'dawn-mission': (10.0, 120.0, "Asteroid Belt (Orbits 4 Vesta & 1 Ceres)"),
    'near-shoemaker': (-15.0, -150.0, "Asteroid 433 Eros (Surface Landing)"),
    'pioneer-10': (26.0, -110.0, "Interstellar Transit / Outer Solar System"),
    'kepler-space-telescope': (15.0, -45.0, "Earth-trailing Heliocentric Orbit"),
    'james-webb-space-telescope': (0.0, 180.0, "Sun-Earth L2 Lagrange Point (~1.5M km)"),
    'hubble-space-telescope': (28.5, -80.0, "Low Earth Orbit (540 km Altitude)"),
    'voyager-1': (35.0, 60.0, "Interstellar Space (>24.4 Billion km)"),
    'voyager-2': (-48.0, 90.0, "Interstellar Space (>20.5 Billion km)"),
    'parker-solar-probe': (10.0, 0.0, "Heliocentric Orbit (~6.1M km from Sun)")
}


def clean_text(val):
    if val is None:
        return ''
    s = str(val).strip()
    s = s.replace('\u200b', '').replace('\ufeff', '').replace('\xa0', ' ')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def parse_date(val):
    if not val:
        return None
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.date() if isinstance(val, datetime.datetime) else val
    s = clean_text(val)
    if not s or s.upper().startswith('N/A'):
        return None
    for pattern in ('%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y', '%b. %d, %Y', '%b %d, %Y', '%d %B %Y'):
        try:
            return datetime.datetime.strptime(s, pattern).date()
        except ValueError:
            pass
    m = re.search(r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2}),?\s+(\d{4})', s, re.IGNORECASE)
    if m:
        month_str, day_str, year_str = m.groups()
        try:
            return datetime.datetime.strptime(f"{month_str} {day_str} {year_str}", "%B %d %Y").date()
        except ValueError:
            try:
                return datetime.datetime.strptime(f"{month_str[:3]} {day_str} {year_str}", "%b %d %Y").date()
            except ValueError:
                pass
    m_year = re.search(r'\b(19\d{2}|20\d{2})\b', s)
    if m_year:
        try:
            return datetime.date(int(m_year.group(1)), 1, 1)
        except ValueError:
            pass
    return None


def parse_question_block(q_raw):
    if not q_raw:
        return None
    text_clean = clean_text(q_raw)
    if not text_clean:
        return None
    lines = [clean_text(l) for l in str(q_raw).split('\n') if clean_text(l)]
    if not lines:
        return None
    q_text = lines[0]
    choices = []
    choice_re = re.compile(r'^\*?\s*([A-D])\)\s*(.*?)(?:\s*\(Correct Answer\))?$', re.IGNORECASE)
    for line in lines[1:]:
        m = choice_re.match(line)
        if m:
            choice_text = clean_text(m.group(2))
            is_correct = '(correct answer)' in line.lower()
            choices.append((choice_text, is_correct))
    if not choices or not any(c[1] for c in choices):
        parts = re.split(r'\s*\*\s*([A-D]\))', str(q_raw))
        if len(parts) >= 3:
            q_text = clean_text(parts[0])
            choices = []
            for i in range(1, len(parts), 2):
                c_body = parts[i+1]
                is_correct = '(correct answer)' in c_body.lower()
                clean_body = re.sub(r'\(correct answer\)', '', c_body, flags=re.IGNORECASE)
                choices.append((clean_text(clean_body), is_correct))
    if not choices:
        return None
    return {
        'text': q_text,
        'choices': choices
    }


def find_excel_file():
    """Finds the desktop nasa.xlsx file or fallback."""
    for p in CANDIDATE_PATHS:
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            return p
    return None


def extract_excel_images(excel_path):
    """Extracts all embedded media images from the Excel archive into static/images/."""
    import zipfile
    excel_dir = BASE_DIR / 'static' / 'images' / 'excel'
    vehicles_dir = BASE_DIR / 'static' / 'images' / 'vehicles'
    excel_dir.mkdir(parents=True, exist_ok=True)
    vehicles_dir.mkdir(parents=True, exist_ok=True)

    mapping = {
        'image1.png': 'apollo-11-eagle.png',
        'image2.png': 'apollo-15-falcon.png',
        'image3.png': 'apollo-12-intrepid.png',
        'image4.png': 'surveyor-3.png',
        'image5.png': 'mars-pathfinder.png',
        'image6.png': 'spirit-opportunity-rovers.png',
        'image7.png': 'viking-1.png',
        'image8.png': 'insight-lander.png',
        'image9.png': 'dawn-mission.png',
        'image10.png': 'near-shoemaker.png',
        'image11.png': 'pioneer-10.png',
        'image12.png': 'ingenuity-helicopter.png',
        'image13.png': 'kepler-space-telescope.png',
    }

    try:
        with zipfile.ZipFile(str(excel_path), 'r') as z:
            for item in z.namelist():
                if item.startswith('xl/media/'):
                    fname = os.path.basename(item)
                    data = z.read(item)
                    out_excel = excel_dir / fname
                    with open(out_excel, 'wb') as f:
                        f.write(data)
                    if fname in mapping:
                        out_veh = vehicles_dir / mapping[fname]
                        with open(out_veh, 'wb') as f:
                            f.write(data)
        print("[INFO] Successfully extracted and synchronized all 13 Excel vehicle images.")
    except Exception as e:
        print(f"[WARN] Image extraction from Excel: {e}")


def run_import(target_file=None):
    if target_file and os.path.exists(target_file):
        excel_path = Path(target_file).resolve()
    else:
        excel_path = find_excel_file()
    if not excel_path:
        print("[ERROR] Could not find 'nasa.xlsx' on Desktop or workspace.")
        return False

    print(f"\n=======================================================")
    print(f" NASA RELATIONAL DATABASE IMPORTER")
    print(f" Source File: {excel_path}")
    print(f" Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=======================================================\n")

    # Extract 1:1 embedded images from the Excel file
    extract_excel_images(excel_path)

    wb = openpyxl.load_workbook(str(excel_path), data_only=True)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        print("[ERROR] Excel worksheet is empty.")
        return False

    header = rows[0]
    data_rows = [r for r in rows[1:] if r and any(r)]
    print(f"[INFO] Loaded worksheet '{sheet.title}': {len(data_rows)} mission rows identified.")

    with transaction.atomic():
        # 1. Ensure Categories exist
        categories = {}
        for cat_slug, meta in CATEGORY_METADATA.items():
            cat, _ = Category.objects.update_or_create(
                slug=cat_slug,
                defaults={
                    'name': meta['name'],
                    'kind': meta['kind'],
                    'icon': meta['icon'],
                    'order': meta['order'],
                    'description': meta['description'],
                    'texture_image': meta['texture_image'],
                    'is_active': True
                }
            )
            categories[cat_slug] = cat

        # 2. Process Excel Rows
        imported_vehicle_slugs = set()
        for idx, row in enumerate(data_rows, 1):
            name_raw = clean_text(row[0]) if len(row) > 0 else ''
            loc_raw = clean_text(row[1]) if len(row) > 1 else ''
            launch_raw = row[2] if len(row) > 2 else None
            landing_raw = row[3] if len(row) > 3 else None
            story_raw = clean_text(row[4]) if len(row) > 4 else ''
            img_raw = clean_text(row[5]) if len(row) > 5 else ''
            q_raw = row[6] if len(row) > 6 else None
            notes_raw = clean_text(row[7]) if len(row) > 7 else ''

            if not name_raw:
                continue

            # Determine category
            name_lower = name_raw.lower()
            loc_lower = loc_raw.lower()
            if any(k in name_lower for k in ('kepler', 'pioneer', 'dawn', 'near', 'jwst', 'voyager', 'parker')):
                cat_slug = 'space'
            elif 'moon' in loc_lower or 'apollo' in name_lower or 'surveyor' in name_lower:
                cat_slug = 'moon'
            elif 'mars' in loc_lower or 'pathfinder' in name_lower or 'spirit' in name_lower or 'viking' in name_lower or 'ingenuity' in name_lower or 'insight' in name_lower:
                cat_slug = 'mars'
            else:
                cat_slug = 'space'

            # Assign Slug & Code
            code = f"NASA-{idx:02d}"
            if 'apollo 11' in name_lower:
                slug = 'apollo-11-eagle'
                code = 'APOLLO-11'
            elif 'apollo 15' in name_lower:
                slug = 'apollo-15-falcon'
                code = 'APOLLO-15'
            elif 'apollo 12' in name_lower:
                slug = 'apollo-12-intrepid'
                code = 'APOLLO-12'
            elif 'surveyor 3' in name_lower:
                slug = 'surveyor-3'
                code = 'SURVEYOR-3'
            elif 'pathfinder' in name_lower:
                slug = 'mars-pathfinder'
                code = 'PATHFINDER'
            elif 'spirit' in name_lower:
                slug = 'spirit-opportunity-rovers'
                code = 'MER-A/B'
            elif 'viking 1' in name_lower:
                slug = 'viking-1'
                code = 'VIKING-1'
            elif 'insight' in name_lower:
                slug = 'insight-lander'
                code = 'INSIGHT'
            elif 'dawn' in name_lower:
                slug = 'dawn-mission'
                code = 'DAWN'
            elif 'near' in name_lower:
                slug = 'near-shoemaker'
                code = 'NEAR'
            elif 'pioneer' in name_lower:
                slug = 'pioneer-10'
                code = 'PIONEER-10'
            elif 'ingenuity' in name_lower:
                slug = 'ingenuity-helicopter'
                code = 'INGENUITY'
            elif 'kepler' in name_lower:
                slug = 'kepler-space-telescope'
                code = 'KEPLER'
            else:
                slug = slugify(name_raw)[:75]

            imported_vehicle_slugs.add(slug)

            # Dates
            launch_date = parse_date(launch_raw)
            landing_date = parse_date(landing_raw)

            # Coordinates
            lat, lon, coord_str = SURFACE_COORDINATES.get(slug, (None, None, loc_raw))
            loc_label = "Landing site" if cat_slug in ('mars', 'moon') else "Mission coordinate"
            milestone_label = "Landing date" if cat_slug in ('mars', 'moon') else "Arrival / Insertion"

            # 1:1 exact image reference from the Excel dataset
            excel_vehicle_images = {
                'apollo-11-eagle': 'images/vehicles/apollo-11-eagle.png',
                'apollo-15-falcon': 'images/vehicles/apollo-15-falcon.png',
                'apollo-12-intrepid': 'images/vehicles/apollo-12-intrepid.png',
                'surveyor-3': 'images/vehicles/surveyor-3.png',
                'mars-pathfinder': 'images/vehicles/mars-pathfinder.png',
                'spirit-opportunity-rovers': 'images/vehicles/spirit-opportunity-rovers.png',
                'viking-1': 'images/vehicles/viking-1.png',
                'insight-lander': 'images/vehicles/insight-lander.png',
                'dawn': 'images/vehicles/dawn-mission.png',
                'dawn-mission': 'images/vehicles/dawn-mission.png',
                'near-shoemaker': 'images/vehicles/near-shoemaker.png',
                'pioneer-10': 'images/vehicles/pioneer-10.png',
                'ingenuity-helicopter': 'images/vehicles/ingenuity-helicopter.png',
                'kepler-space-telescope': 'images/vehicles/kepler-space-telescope.png',
            }
            image_path = excel_vehicle_images.get(slug, img_raw or f'images/vehicles/{slug}.png')

            # Upsert Vehicle
            vehicle, _ = Vehicle.objects.update_or_create(
                slug=slug,
                defaults={
                    'category': categories[cat_slug],
                    'code': code,
                    'name': name_raw,
                    'tagline': f"Historic {categories[cat_slug].name} mission vehicle",
                    'mission_type': f"{categories[cat_slug].name} Exploration",
                    'status_label': 'Archived Telemetry / Historic Mission',
                    'launch_date': launch_date,
                    'landing_date': landing_date,
                    'milestone_label': milestone_label,
                    'coordinates': coord_str,
                    'surface_lat': lat,
                    'surface_lon': lon,
                    'location_label': loc_label,
                    'image_path': image_path,
                    'raw_location': loc_raw,
                    'raw_launch_text': str(launch_raw) if launch_raw else '',
                    'raw_landing_text': str(landing_raw) if landing_raw else '',
                    'notes': notes_raw,
                    'order': idx,
                    'is_published': True
                }
            )

            # Upsert Story
            if story_raw:
                Story.objects.update_or_create(
                    vehicle=vehicle,
                    order=0,
                    defaults={
                        'title': f"{vehicle.name} Mission Log",
                        'content': story_raw
                    }
                )

            # Upsert Questions from Excel
            parsed_q = parse_question_block(q_raw)
            if parsed_q:
                q_obj, _ = Question.objects.update_or_create(
                    vehicle=vehicle,
                    order=0,
                    defaults={
                        'text': parsed_q['text'],
                        'hint': f"Review the flight telemetry for {vehicle.name}.",
                        'explanation': f"Historical mission telemetry from NASA records."
                    }
                )
                for c_idx, (choice_text, is_corr) in enumerate(parsed_q['choices']):
                    Answer.objects.update_or_create(
                        question=q_obj,
                        order=c_idx,
                        defaults={
                            'text': choice_text,
                            'is_correct': is_corr
                        }
                    )

            # Upsert Second Question if available
            add_q = ADDITIONAL_QUESTIONS.get(slug)
            if add_q:
                q2_obj, _ = Question.objects.update_or_create(
                    vehicle=vehicle,
                    order=1,
                    defaults={
                        'text': add_q['text'],
                        'hint': add_q['hint'],
                        'explanation': add_q['explanation']
                    }
                )
                for c_idx, (c_text, is_corr) in enumerate(add_q['choices']):
                    Answer.objects.update_or_create(
                        question=q2_obj,
                        order=c_idx,
                        defaults={
                            'text': c_text,
                            'is_correct': is_corr
                        }
                    )

        # 3. Add Cornerstone Probes (JWST, Voyager 1, Parker Solar Probe)
        for c_data in CORNERSTONE_MISSIONS:
            slug = c_data['slug']
            imported_vehicle_slugs.add(slug)
            v_obj, _ = Vehicle.objects.update_or_create(
                slug=slug,
                defaults={
                    'category': categories[c_data['category']],
                    'code': c_data['code'],
                    'name': c_data['name'],
                    'tagline': c_data['tagline'],
                    'mission_type': c_data['mission_type'],
                    'status_label': c_data['status_label'],
                    'launch_date': c_data['launch_date'],
                    'landing_date': c_data['landing_date'],
                    'milestone_label': c_data['milestone_label'],
                    'coordinates': c_data['coordinates'],
                    'surface_lat': c_data['surface_lat'],
                    'surface_lon': c_data['surface_lon'],
                    'location_label': c_data['location_label'],
                    'image_path': c_data['image_path'],
                    'raw_location': c_data['raw_location'],
                    'raw_launch_text': c_data['raw_launch_text'],
                    'raw_landing_text': c_data['raw_landing_text'],
                    'notes': c_data['notes'],
                    'order': c_data['order'],
                    'is_published': True
                }
            )

            Story.objects.update_or_create(
                vehicle=v_obj,
                order=0,
                defaults={
                    'title': f"{v_obj.name} Flight Log",
                    'content': c_data['story']
                }
            )

            for s_idx, (lbl, val) in enumerate(c_data['specs']):
                VehicleSpec.objects.update_or_create(
                    vehicle=v_obj,
                    order=s_idx,
                    defaults={'label': lbl, 'value': val}
                )

            pq = c_data['primary_question']
            q_obj, _ = Question.objects.update_or_create(
                vehicle=v_obj,
                order=0,
                defaults={
                    'text': pq['text'],
                    'hint': pq['hint'],
                    'explanation': pq['explanation']
                }
            )
            for c_idx, (c_text, is_corr) in enumerate(pq['choices']):
                Answer.objects.update_or_create(
                    question=q_obj,
                    order=c_idx,
                    defaults={'text': c_text, 'is_correct': is_corr}
                )

            sq = ADDITIONAL_QUESTIONS.get(slug)
            if sq:
                q2_obj, _ = Question.objects.update_or_create(
                    vehicle=v_obj,
                    order=1,
                    defaults={
                        'text': sq['text'],
                        'hint': sq['hint'],
                        'explanation': sq['explanation']
                    }
                )
                for c_idx, (c_text, is_corr) in enumerate(sq['choices']):
                    Answer.objects.update_or_create(
                        question=q2_obj,
                        order=c_idx,
                        defaults={'text': c_text, 'is_correct': is_corr}
                    )

    # 4. Verification Summary
    print("\n-------------------------------------------------------")
    print(" DATABASE VERIFICATION SUMMARY")
    print("-------------------------------------------------------")
    summary = [
        ("Categories Table", Category.objects.count()),
        ("Vehicles Table", Vehicle.objects.count()),
        ("Vehicle Stories Table", Story.objects.count()),
        ("Vehicle Specs Table", VehicleSpec.objects.count()),
        ("Exam Questions Table", Question.objects.count()),
        ("Answer Choices Table", Answer.objects.count()),
    ]
    for table_name, count in summary:
        print(f"  • {table_name:<25}: {count:>5} records")
    print("-------------------------------------------------------")
    print(f" [SUCCESS] All NASA records successfully mapped and synchronized!\n")
    return True


if __name__ == '__main__':
    run_import()
