import json
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from votecount.models import (
    Agent,
    Circunscricao,
    Country,
    District,
    PollingStation,
    VoteEntry,
    VoteTable,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Import voting data from JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file", type=str, help="Path to the JSON file containing voting data"
        )
        parser.add_argument(
            "--country",
            type=str,
            default="São Tomé e Príncipe",
            help="Country name (default: São Tomé e Príncipe)",
        )
        parser.add_argument(
            "--country-code",
            type=str,
            default="STP",
            help="Country code (default: STP)",
        )
        parser.add_argument(
            "--clear", action="store_true", help="Clear existing data before importing"
        )
        parser.add_argument(
            "--user-email",
            type=str,
            default="admin@example.com",
            help="User email for Agent association",
        )

    def handle(self, *args, **options):
        json_file_path = options["json_file"]
        country_name = options["country"]
        country_code = options["country_code"]
        clear_existing = options.get("clear", False)
        user_email = options.get("user_email")

        # Validate file exists
        if not os.path.exists(json_file_path):
            raise CommandError(f"JSON file not found: {json_file_path}")

        # Read JSON data
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise CommandError(f"Error reading file: {e}")

        if not isinstance(data, list):
            raise CommandError("JSON data must be a list of district objects")

        self.stdout.write(f"📂 Found {len(data)} districts to import...")

        try:
            with transaction.atomic():
                # Get or create country
                country, created = Country.objects.get_or_create(
                    name=country_name,
                    defaults={"code": country_code, "total_deputies": 55},
                )

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Created new country: {country_name}")
                    )
                else:
                    self.stdout.write(f"ℹ️ Using existing country: {country_name}")

                # Get or create agent
                user, _ = User.objects.get_or_create(
                    email=user_email, defaults={"username": user_email.split("@")[0]}
                )
                agent, _ = Agent.objects.get_or_create(user=user)

                # Clear existing data if requested
                if clear_existing:
                    self.clear_existing_data(country)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Cleared existing data for {country_name}"
                        )
                    )

                # Process each district
                total_tables = 0
                total_circunscricoes = set()
                processed_districts = 0
                total_voters = 0

                for district_data in data:
                    district_info = district_data.get("distrito", {})
                    if not district_info:
                        self.stdout.write(
                            self.style.WARNING("⚠️ Skipping empty district data")
                        )
                        continue

                    result = self.process_district(district_info, country)
                    processed_districts += 1
                    total_tables += result["tables"]
                    total_circunscricoes.update(result["circunscricoes"])
                    total_voters += result["voters"]

                    self.stdout.write(
                        f"  ✅ {district_info.get('name', 'Unknown')}: "
                        f"{len(result['circunscricoes'])} circunscrições, "
                        f"{result['tables']} tables, "
                        f"{result['voters']:,} voters"
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✅ Import completed successfully!\n"
                        f"  Districts processed: {processed_districts}\n"
                        f"  Circunscrições created: {len(total_circunscricoes)}\n"
                        f"  Vote tables created: {total_tables}\n"
                        f"  Total voters: {total_voters:,}\n"
                    )
                )

                # Print summary
                self.print_summary(country)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Import failed: {e!s}"))
            raise

    def process_district(self, district_info, country):
        """Process a single district and all its localidades"""

        district_name = district_info.get("name", "Unknown")
        district_sigla = district_info.get("sigla", "UNK")
        localidades = district_info.get("localidades", [])

        # Get or create district
        district, created = District.objects.get_or_create(
            name=district_name, sigla=district_sigla, country=country
        )

        if created:
            self.stdout.write(
                f"  📍 Creating district: {district_name} ({district_sigla})"
            )

        # Track unique circunscrições
        circunscricao_codes = set()
        table_count = 0
        total_voters = 0

        # Process each localidade (vote table)
        for localidade in localidades:
            try:
                circunscricao_code = localidade.get("Circunscrição")
                if not circunscricao_code:
                    self.stdout.write(
                        self.style.WARNING("    ⚠️ Missing Circunscrição in localidade")
                    )
                    continue

                circunscricao_codes.add(circunscricao_code)

                # Process the vote table
                self.process_vote_table(localidade, district, circunscricao_code)
                table_count += 1
                total_voters += localidade.get("Eleitores", 0)

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"    ⚠️ Error processing {localidade.get('Circunscrição', 'Unknown')}: {e!s}"
                    )
                )
                raise

        return {
            "circunscricoes": circunscricao_codes,
            "tables": table_count,
            "voters": total_voters,
        }

    def process_vote_table(self, localidade, district, circunscricao_code):
        """Process a single vote table"""

        # Get or create circunscrição
        circunscricao, created = Circunscricao.objects.get_or_create(
            code=circunscricao_code, defaults={"district": district}
        )

        # Get polling station
        polling_station_name = localidade.get("Local da(s) Mesa(s) de Voto", "Unknown")
        polling_station, created = PollingStation.objects.get_or_create(
            name=polling_station_name, defaults={"circunscricao": circunscricao}
        )

        # If polling station existed but belonged to a different circunscrição, update it
        if not created and polling_station.circunscricao != circunscricao:
            polling_station.circunscricao = circunscricao
            polling_station.save()

        # Create vote table
        letters = localidade.get("Letras", "A")
        table_code = f"{circunscricao_code}-{letters}"

        vote_table, created = VoteTable.objects.get_or_create(
            code=table_code,
            circunscricao=circunscricao,
            defaults={
                "polling_station": polling_station,
                "total_voters": localidade.get("Eleitores", 0),
                "location_details": localidade.get("Localidade(s)", ""),
            },
        )

        if not created:
            # Update existing table
            vote_table.polling_station = polling_station
            vote_table.total_voters = localidade.get("Eleitores", 0)
            vote_table.location_details = localidade.get("Localidade(s)", "")
            vote_table.save()

        return vote_table

    def clear_existing_data(self, country):
        """Clear all data for a country"""
        # Delete in correct order to avoid foreign key violations

        # Delete vote entries (through vote tables)
        VoteEntry.objects.filter(
            vote_table__circunscricao__district__country=country
        ).delete()

        # Delete vote tables
        VoteTable.objects.filter(circunscricao__district__country=country).delete()

        # Delete polling stations
        PollingStation.objects.filter(circunscricao__district__country=country).delete()

        # Delete circunscrições
        Circunscricao.objects.filter(district__country=country).delete()

        # Delete districts (but keep country)
        District.objects.filter(country=country).delete()

        self.stdout.write(f"  ✅ Cleared all data for {country.name}")

    def print_summary(self, country):
        """Print summary statistics"""
        from django.db.models import Count, Sum

        total_districts = District.objects.filter(country=country).count()
        total_circunscricoes = Circunscricao.objects.filter(
            district__country=country
        ).count()
        total_tables = VoteTable.objects.filter(
            circunscricao__district__country=country
        ).count()
        total_voters = (
            VoteTable.objects.filter(
                circunscricao__district__country=country
            ).aggregate(total=Sum("total_voters"))["total"]
            or 0
        )

        # Get districts with their table counts
        districts = (
            District.objects.filter(country=country)
            .annotate(
                table_count=Count("circunscricoes__vote_tables"),
                voter_count=Sum("circunscricoes__vote_tables__total_voters"),
            )
            .order_by("name")
        )

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 IMPORT SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Country: {country.name} ({country.code})")
        self.stdout.write(f"Total Districts: {total_districts}")
        self.stdout.write(f"Total Circunscrições: {total_circunscricoes}")
        self.stdout.write(f"Total Vote Tables: {total_tables}")
        self.stdout.write(f"Total Registered Voters: {total_voters:,}")

        self.stdout.write("\n📋 Districts Summary:")
        self.stdout.write("-" * 60)
        for district in districts:
            self.stdout.write(
                f"  {district.name} ({district.sigla}): "
                f"{district.table_count} tables, "
                f"{district.voter_count or 0:,} voters"
            )
        self.stdout.write("=" * 60)
