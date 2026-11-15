from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Imports mission educational content and questions into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default=None,
            help='Optional path to data source.'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Verifying and syncing educational mission data..."))
        file_arg = options.get('file')
        if file_arg:
            call_command('import_excel_data', file=file_arg)
        else:
            call_command('import_excel_data')
        self.stdout.write(self.style.SUCCESS("Mission data synchronized successfully."))
