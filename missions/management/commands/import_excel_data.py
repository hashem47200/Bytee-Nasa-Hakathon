"""
Django Management Command: import_excel_data
============================================
Delegates directly to the authoritative NASA Relational Database Importer in scripts.import_nasa.
"""

import sys
from pathlib import Path
from django.core.management.base import BaseCommand

# Ensure project root is available on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_nasa import run_import


class Command(BaseCommand):
    help = "Imports mission educational content, specs, and questions from nasa.xlsx."

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default=None, help='Optional path to data source.')

    def handle(self, *args, **options):
        run_import(options.get('file'))


if __name__ == '__main__':
    run_import()
