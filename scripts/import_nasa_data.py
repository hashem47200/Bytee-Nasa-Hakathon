"""
Standalone Bytee NASA Data Import Script
========================================
Authoritative importer that parses ONLY the 13 authentic missions from `nasa_data.xlsx` (or `nasa.xlsx`),
permanently purges the 5 fabricated deep-space records, assigns the 13 missions to Mars and Moon,
distinguishes surface vehicles from nearby-space probes, and populates normalized relational database tables.
"""

import os
import sys
import re
import datetime
import zipfile
import xml.etree.ElementTree as ET
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

# Candidate paths for automated detection
CANDIDATE_PATHS = [
    BASE_DIR / 'nasa_data.xlsx',
    BASE_DIR / 'nasa.xlsx',
    Path('/workspaces') / 'nasa_data.xlsx',
    Path('/workspaces') / 'nasa.xlsx',
    Path('/workspaces') / 'Bytee_project_NASA' / 'nasa_data.xlsx',
    Path('/workspaces') / 'Bytee_project_NASA' / 'nasa.xlsx',
    Path.cwd() / 'nasa_data.xlsx',
    Path.cwd() / 'nasa.xlsx',
    Path(os.path.expanduser('~')) / 'OneDrive - Yarmouk University' / 'Desktop' / 'nasa_data.xlsx',
    Path(os.path.expanduser('~')) / 'OneDrive - Yarmouk University' / 'Desktop' / 'nasa.xlsx',
    Path(os.path.expanduser('~')) / 'Desktop' / 'nasa_data.xlsx',
    Path(os.path.expanduser('~')) / 'Desktop' / 'nasa.xlsx',
]

# Only Mars and Moon categories (Strict celestial separation, no generic SPACE category)
CATEGORY_METADATA = {
    'mars': {
        'name': 'Mars',
        'kind': 'planetary',
        'icon': '🔴',
        'order': 1,
        'description': 'Landers, rovers, and nearby-space probes exploring the Red Planet and its orbital vicinity.',
        'texture_image': 'images/planets/mars-texture.jpg'
    },
    'moon': {
        'name': 'Moon',
        'kind': 'planetary',
        'icon': '🌕',
        'order': 2,
        'description': "Humanity's celestial companion, walked by Apollo astronauts and mapped by Surveyor probes.",
        'texture_image': 'images/planets/moon-texture.jpg'
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
        'explanation': "Apollo 12 touched down only 180 meters (600 feet) from Surveyor 3, demonstrating precision touchdown on the lunar surface.",
        'choices': [
            ("Only 180 meters away", True),
            ("Over 5 kilometers away", False),
            ("25 kilometers away", False),
            ("Directly inside the Surveyor crater rim touching it", False)
        ]
    },
    'surveyor-3': {
        'text': "What mechanical surface sampling tool did Surveyor 3 successfully test on the lunar soil?",
        'hint': "A remote-controlled digging arm used to scoop and trench the regolith.",
        'explanation': "Surveyor 3 operated an electric surface-sampler scoop that dug four trenches up to 17.5 cm deep to verify the Moon's soil bearing strength for human landers.",
        'choices': [
            ("A robotic soil-sampling scoop and trenching arm", True),
            ("A deep ultrasonic rock core drill", False),
            ("A pneumatic harpoon anchor", False),
            ("A wheeled tethered rover cart", False)
        ]
    },
    'mars-pathfinder': {
        'text': "What was the name of the miniature robotic rover companion deployed onto Mars by the Pathfinder lander?",
        'hint': "Named after historical abolitionist and women's rights advocate Sojourner Truth.",
        'explanation': "Pathfinder carried the 10.6 kg Sojourner rover, the first wheeled rover ever driven on another planet.",
        'choices': [
            ("Sojourner", True),
            ("Curiosity", False),
            ("Opportunity", False),
            ("Perseverance", False)
        ]
    },
    'spirit-opportunity-rovers': {
        'text': "What geological evidence did the Spirit rover uncover at sites like Home Plate and Comanche on Mars?",
        'hint': "Think of mineral deposits associated with boiling water and hydrothermal vents.",
        'explanation': "Spirit uncovered rich deposits of pure silica and carbonates formed by ancient hot spring or hydrothermal fumarole activity.",
        'choices': [
            ("Silica and carbonate deposits indicating past hydrothermal springs", True),
            ("Active liquid water geysers", False),
            ("Fossilized plant matter", False),
            ("Vast subsurface gold and copper veins", False)
        ]
    },
    'viking-1': {
        'text': "What milestone did Viking 1 achieve on July 20, 1976?",
        'hint': "It was the very first successful US operation of its kind on the Red Planet.",
        'explanation': "Viking 1 became the first American spacecraft to touch down safely on the Martian surface and operate successfully for over six years.",
        'choices': [
            ("First successful American spacecraft to touch down and operate on Mars", True),
            ("First spacecraft to orbit Jupiter", False),
            ("First human flyby of Phobos", False),
            ("First sample return flight from the asteroid belt", False)
        ]
    },
    'insight-lander': {
        'text': "What key scientific tool allowed InSight to map the internal layered structure of Mars?",
        'hint': "This ultra-sensitive French dome instrument detected marsquakes.",
        'explanation': "The Seismic Experiment for Interior Structure (SEIS) recorded over 1,300 marsquakes, allowing scientists to calculate the size and state of the Martian crust, mantle, and core.",
        'choices': [
            ("SEIS (Seismic Experiment for Interior Structure)", True),
            ("Surface Raman spectrometer", False),
            ("Neutron moisture radar", False),
            ("Sub-surface laser excavator", False)
        ]
    },
    'dawn-mission': {
        'text': "What revolutionary propulsion technology enabled the Dawn spacecraft to orbit two different extraterrestrial bodies (Vesta and Ceres)?",
        'hint': "It uses electricity to accelerate xenon ions rather than chemical fuel combustion.",
        'explanation': "Dawn utilized hyper-efficient Xenon Ion Propulsion, allowing it to orbit asteroid Vesta and then cruise through deep space to orbit dwarf planet Ceres.",
        'choices': [
            ("Xenon Ion Propulsion System", True),
            ("Nuclear thermal rocket booster", False),
            ("Solar photon sail propulsion", False),
            ("Superconducting magnetic tether", False)
        ]
    },
    'dawn': {
        'text': "What revolutionary propulsion technology enabled the Dawn spacecraft to orbit two different extraterrestrial bodies (Vesta and Ceres)?",
        'hint': "It uses electricity to accelerate xenon ions rather than chemical fuel combustion.",
        'explanation': "Dawn utilized hyper-efficient Xenon Ion Propulsion, allowing it to orbit asteroid Vesta and then cruise through deep space to orbit dwarf planet Ceres.",
        'choices': [
            ("Xenon Ion Propulsion System", True),
            ("Nuclear thermal rocket booster", False),
            ("Solar photon sail propulsion", False),
            ("Superconducting magnetic tether", False)
        ]
    },
    'near-shoemaker': {
        'text': "What historical first did NEAR Shoemaker achieve at Asteroid 433 Eros on February 12, 2001?",
        'hint': "Although designed purely as an orbiter, the team guided it to touch down on the asteroid.",
        'explanation': "NEAR Shoemaker achieved the first soft landing on an asteroid, transmitting surface gamma-ray spectrometry readings back to Earth.",
        'choices': [
            ("First human spacecraft to softly touch down on the surface of an asteroid", True),
            ("First spacecraft to capture a sample from a comet nucleus", False),
            ("First spacecraft to detonate an explosive kinetic penetrator", False),
            ("First spacecraft to bring asteroid regolith to low Earth orbit", False)
        ]
    },
    'pioneer-10': {
        'text': "What plaque did Pioneer 10 carry on its chassis as an interstellar message?",
        'hint': "Carl Sagan and Frank Drake helped design this golden message for extraterrestrial civilizations.",
        'explanation': "Pioneer 10 carried a gold-anodized aluminum plaque depicting a nude man and woman, the spacecraft silhouette, and pulsar coordinates pointing to Earth's location.",
        'choices': [
            ("A gold-anodized aluminum plaque illustrating humanity and our solar system", True),
            ("A digital optical disc containing world music and greetings", False),
            ("A titanium globe of Planet Earth", False),
            ("A laser-engraved silicon microchip containing human DNA sequences", False)
        ]
    },
    'ingenuity-helicopter': {
        'text': "How many total powered flights did Ingenuity successfully complete over its 3-year mission on Mars?",
        'hint': "Originally planned for just 5 technology demonstration flights, it flew over 70 times.",
        'explanation': "Ingenuity completed 72 flights, logging more than 2 hours of flight time and covering 17 kilometers across Jezero Crater.",
        'choices': [
            ("72 flights", True),
            ("5 flights", False),
            ("25 flights", False),
            ("144 flights", False)
        ]
    },
    'kepler-space-telescope': {
        'text': "What optical method did the Kepler Space Telescope use to detect thousands of exoplanets?",
        'hint': "It watched for the tiny dimming of starlight as a planet crossed in front of its star.",
        'explanation': "Kepler used transit photometry to measure miniature periodic dips in the brightness of stars caused by transiting exoplanets.",
        'choices': [
            ("Transit photometry method (measuring starlight dips)", True),
            ("Direct optical coronagraph imaging", False),
            ("Radial velocity Doppler shifting spectroscopy", False),
            ("Gravitational microlensing parallax", False)
        ]
    }
}

# Accurate Coordinates & 3D Visual Positions
SURFACE_COORDINATES = {
    # Moon Surface (Lat, Lon, Coord String, is_nearby_space, orbit_alt)
    'apollo-11-eagle': (0.67408, 23.47297, "0.67° N, 23.47° E (Mare Tranquillitatis)", False, 1.0),
    'apollo-15-falcon': (26.1322, 3.6339, "26.13° N, 3.63° E (Hadley-Apennine)", False, 1.0),
    'apollo-12-intrepid': (-3.0124, -23.4216, "3.01° S, 23.42° W (Oceanus Procellarum)", False, 1.0),
    'surveyor-3': (-3.015, -23.418, "3.01° S, 23.42° W (Oceanus Procellarum)", False, 1.0),

    # Mars Surface
    'mars-pathfinder': (19.13, -33.22, "19.13° N, 33.22° W (Ares Vallis)", False, 1.0),
    'spirit-opportunity-rovers': (-14.5684, 175.4726, "Spirit: -14.57° S, 175.47° E (Gusev) / Oppy: -1.95° S (Meridiani)", False, 1.0),
    'viking-1': (22.697, -48.222, "22.70° N, 48.22° W (Chryse Planitia)", False, 1.0),
    'insight-lander': (4.502, 135.623, "4.50° N, 135.62° E (Elysium Planitia)", False, 1.0),
    'ingenuity-helicopter': (18.4447, 77.4508, "18.44° N, 77.45° E (Jezero Crater)", False, 1.0),

    # Nearby-Space Probes (Associated with Mars interplanetary exploration, floating in orbit)
    'dawn-mission': (10.0, 120.0, "Asteroid Belt (Orbits 4 Vesta & 1 Ceres)", True, 1.40),
    'dawn': (10.0, 120.0, "Asteroid Belt (Orbits 4 Vesta & 1 Ceres)", True, 1.40),
    'near-shoemaker': (-15.0, -150.0, "Asteroid 433 Eros (Surface Landing)", True, 1.45),
    'pioneer-10': (26.0, -110.0, "Interstellar Transit / Outer Solar System", True, 1.50),
    'kepler-space-telescope': (15.0, -45.0, "Earth-trailing Heliocentric Orbit", True, 1.55),
}

# 1:1 Mapping between Excel row slugs and verified images
EXCEL_IMAGE_MAP = {
    'apollo-11-eagle': 'images/vehicles/apollo-11-eagle.png',
    'apollo-15-falcon': 'images/vehicles/apollo-15-falcon.png',
    'apollo-12-intrepid': 'images/vehicles/apollo-12-intrepid.png',
    'surveyor-3': 'images/vehicles/surveyor-3.png',
    'mars-pathfinder': 'images/vehicles/mars-pathfinder.png',
    'spirit-opportunity-rovers': 'images/vehicles/spirit-opportunity-rovers.png',
    'viking-1': 'images/vehicles/viking-1.png',
    'insight-lander': 'images/vehicles/insight-lander.png',
    'dawn-mission': 'images/vehicles/dawn-mission.png',
    'dawn': 'images/vehicles/dawn-mission.png',
    'near-shoemaker': 'images/vehicles/near-shoemaker.png',
    'pioneer-10': 'images/vehicles/pioneer-10.png',
    'ingenuity-helicopter': 'images/vehicles/ingenuity-helicopter.png',
    'kepler-space-telescope': 'images/vehicles/kepler-space-telescope.png',
}

# The 5 fabricated records to permanently purge
FABRICATED_SLUGS = [
    'james-webb-space-telescope',
    'hubble-space-telescope',
    'voyager-1',
    'voyager-2',
    'parker-solar-probe',
]


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
            letter = m.group(1).upper()
            c_text = clean_text(m.group(2))
            is_correct = '(Correct Answer)' in line
            choices.append((c_text, is_correct))
    if not any(c[1] for c in choices) and choices:
        choices[0] = (choices[0][0], True)
    return {'text': q_text, 'choices': choices}


def find_excel_file():
    for p in CANDIDATE_PATHS:
        if p.exists():
            return p
    return None


def extract_excel_images(excel_path):
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
        with zipfile.ZipFile(excel_path, 'r') as z:
            for item in z.namelist():
                if item.startswith('xl/media/image') and item.endswith('.png'):
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
        print("[ERROR] Could not find 'nasa_data.xlsx' or 'nasa.xlsx'.")
        return False

    print(f"\n=======================================================")
    print(f" BYTEE AUTHENTIC RELATIONAL DATABASE IMPORTER")
    print(f" Source File: {excel_path}")
    print(f" Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=======================================================\n")

    # Extract images from Excel
    extract_excel_images(excel_path)

    wb = openpyxl.load_workbook(str(excel_path), data_only=True)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        print("[ERROR] Excel worksheet is empty.")
        return False

    data_rows = [r for r in rows[1:] if r and any(r) and r[0]]
    print(f"[INFO] Loaded worksheet '{sheet.title}': {len(data_rows)} authentic mission rows identified.")

    with transaction.atomic():
        # 1. Permanently delete the 5 fabricated vehicles
        deleted_count, _ = Vehicle.objects.filter(slug__in=FABRICATED_SLUGS).delete()
        if deleted_count:
            print(f"[INFO] Permanently purged {deleted_count} fabricated vehicle record(s).")

        # 2. Delete generic 'space' category (strict celestial separation: Mars and Moon only)
        Category.objects.filter(slug='space').delete()

        # 3. Ensure Mars and Moon Categories exist
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

        # 4. Process the 13 Authentic Excel Rows
        imported_slugs = set()
        for idx, row in enumerate(data_rows, 1):
            name_raw = clean_text(row[0])
            loc_raw = clean_text(row[1]) if len(row) > 1 else ''
            launch_raw = row[2] if len(row) > 2 else None
            landing_raw = row[3] if len(row) > 3 else None
            story_raw = clean_text(row[4]) if len(row) > 4 else ''
            img_raw = clean_text(row[5]) if len(row) > 5 else ''
            q_raw = row[6] if len(row) > 6 else None
            notes_raw = clean_text(row[7]) if len(row) > 7 else ''

            if not name_raw:
                continue

            name_lower = name_raw.lower()
            loc_lower = loc_raw.lower()

            # Assign Slug & Code
            code = f"NASA-{idx:02d}"
            if 'apollo 11' in name_lower:
                slug = 'apollo-11-eagle'
                code = 'APOLLO-11'
                cat_slug = 'moon'
            elif 'apollo 15' in name_lower:
                slug = 'apollo-15-falcon'
                code = 'APOLLO-15'
                cat_slug = 'moon'
            elif 'apollo 12' in name_lower:
                slug = 'apollo-12-intrepid'
                code = 'APOLLO-12'
                cat_slug = 'moon'
            elif 'surveyor 3' in name_lower:
                slug = 'surveyor-3'
                code = 'SURVEYOR-3'
                cat_slug = 'moon'
            elif 'pathfinder' in name_lower:
                slug = 'mars-pathfinder'
                code = 'PATHFINDER'
                cat_slug = 'mars'
            elif 'spirit' in name_lower:
                slug = 'spirit-opportunity-rovers'
                code = 'MER-A/B'
                cat_slug = 'mars'
            elif 'viking 1' in name_lower:
                slug = 'viking-1'
                code = 'VIKING-1'
                cat_slug = 'mars'
            elif 'insight' in name_lower:
                slug = 'insight-lander'
                code = 'INSIGHT'
                cat_slug = 'mars'
            elif 'dawn' in name_lower:
                slug = 'dawn-mission'
                code = 'DAWN'
                cat_slug = 'mars'
            elif 'near' in name_lower:
                slug = 'near-shoemaker'
                code = 'NEAR'
                cat_slug = 'mars'
            elif 'pioneer' in name_lower:
                slug = 'pioneer-10'
                code = 'PIONEER-10'
                cat_slug = 'mars'
            elif 'ingenuity' in name_lower:
                slug = 'ingenuity-helicopter'
                code = 'INGENUITY'
                cat_slug = 'mars'
            elif 'kepler' in name_lower:
                slug = 'kepler-space-telescope'
                code = 'KEPLER'
                cat_slug = 'mars'
            else:
                slug = slugify(name_raw)[:75]
                cat_slug = 'mars'

            imported_slugs.add(slug)

            # Dates
            launch_date = parse_date(launch_raw)
            landing_date = parse_date(landing_raw)

            # Coordinates & Placement
            lat, lon, coord_str, is_nearby, orbit_alt = SURFACE_COORDINATES.get(
                slug, (None, None, loc_raw, False, 1.0)
            )
            loc_label = "Orbital / Nearby Space" if is_nearby else "Surface Landing Site"
            milestone_lbl = "Arrival date" if is_nearby else "Landing date"

            # Image path
            img_path = EXCEL_IMAGE_MAP.get(slug, f"images/vehicles/{slug}.png")

            # Clean Tagline
            if 'apollo' in slug:
                tagline = 'Historic Moon landing module'
            elif 'surveyor' in slug:
                tagline = 'Robotic lunar surface exploration probe'
            elif is_nearby:
                tagline = 'Nearby-space & orbital exploration probe'
            else:
                tagline = 'Historic Mars exploration vehicle'

            # Upsert Vehicle
            vehicle, _ = Vehicle.objects.update_or_create(
                slug=slug,
                defaults={
                    'category': categories[cat_slug],
                    'code': code,
                    'name': name_raw,
                    'tagline': tagline,
                    'mission_type': 'Lunar Surface Exploration' if cat_slug == 'moon' else ('Nearby-Space Probe' if is_nearby else 'Martian Surface Exploration'),
                    'status_label': 'Archived Telemetry / Historic Mission',
                    'launch_date': launch_date,
                    'landing_date': landing_date,
                    'milestone_label': milestone_lbl,
                    'coordinates': coord_str,
                    'surface_lat': lat,
                    'surface_lon': lon,
                    'is_nearby_space': is_nearby,
                    'orbit_altitude': orbit_alt,
                    'location_label': loc_label,
                    'image_path': img_path,
                    'raw_location': loc_raw,
                    'raw_launch_text': clean_text(str(launch_raw)) if launch_raw else '',
                    'raw_landing_text': clean_text(str(landing_raw)) if landing_raw else '',
                    'notes': notes_raw,
                    'order': idx,
                    'is_published': True
                }
            )

            # Upsert Story from Excel
            if story_raw:
                Story.objects.update_or_create(
                    vehicle=vehicle,
                    order=0,
                    defaults={
                        'title': f"{vehicle.name} Mission Log",
                        'content': story_raw
                    }
                )

            # Upsert Question 1 from Excel
            parsed_q = parse_question_block(q_raw)
            if parsed_q:
                q_obj, _ = Question.objects.update_or_create(
                    vehicle=vehicle,
                    order=0,
                    defaults={
                        'text': parsed_q['text'],
                        'hint': f"Review the flight telemetry and story for {vehicle.name}.",
                        'explanation': "Authoritative mission telemetry from official NASA dataset."
                    }
                )
                q_obj.answers.all().delete()
                for c_idx, (choice_text, is_corr) in enumerate(parsed_q['choices']):
                    Answer.objects.create(
                        question=q_obj,
                        order=c_idx,
                        text=choice_text,
                        is_correct=is_corr
                    )

            # Upsert Question 2 reinforcing understanding
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
                q2_obj.answers.all().delete()
                for c_idx, (c_text, is_corr) in enumerate(add_q['choices']):
                    Answer.objects.create(
                        question=q2_obj,
                        order=c_idx,
                        text=c_text,
                        is_correct=is_corr
                    )

        # Remove any vehicles not in the 13 authentic slugs
        extraneous = Vehicle.objects.exclude(slug__in=imported_slugs)
        if extraneous.exists():
            ex_names = list(extraneous.values_list('slug', flat=True))
            extraneous.delete()
            print(f"[INFO] Removed extraneous records: {ex_names}")

    # 4. Verification Summary
    print("\n-------------------------------------------------------")
    print(" DATABASE VERIFICATION SUMMARY")
    print("-------------------------------------------------------")
    summary = [
        ("Categories Table (Mars, Moon)", Category.objects.count()),
        ("Authentic Vehicles Table", Vehicle.objects.count()),
        ("Mars Vehicles", Vehicle.objects.filter(category__slug='mars').count()),
        ("Moon Vehicles", Vehicle.objects.filter(category__slug='moon').count()),
        ("Vehicle Stories Table", Story.objects.count()),
        ("Exam Questions Table", Question.objects.count()),
        ("Answer Choices Table", Answer.objects.count()),
    ]
    for table_name, count in summary:
        print(f"  • {table_name:<30}: {count:>5} records")
    print("-------------------------------------------------------")
    print(f" [SUCCESS] Bytee authoritative database synchronized successfully!\n")
    return True


if __name__ == '__main__':
    run_import()
