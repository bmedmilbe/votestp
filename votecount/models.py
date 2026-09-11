from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Avg, Count, Max, Min, Sum

# ============================================
# CUSTOM MODEL MANAGERS
# ============================================


class AgentManager(models.Manager):
    """Custom manager for Agent model with optimized queries"""

    def get_queryset(self):
        return super().get_queryset().select_related("user")

    def with_user_data(self):
        """Get agents with user data preloaded"""
        return self.get_queryset().select_related("user")

    def get_by_user(self, user_id):
        """Get agent by user ID"""
        return self.get_queryset().filter(user_id=user_id).first()


class CountryManager(models.Manager):
    """Custom manager for Country model with optimized queries"""

    def get_queryset(self):
        return super().get_queryset()

    def with_district_counts(self):
        """Get countries with district counts"""
        return self.get_queryset().annotate(
            districts_count=Count("districts", distinct=True)
        )

    def with_vote_table_counts(self):
        """Get countries with vote table counts"""
        return self.get_queryset().annotate(
            vote_tables_count=Count(
                "districts__circunscricoes__vote_tables", distinct=True
            )
        )

    def with_full_stats(self):
        """Get countries with all statistics"""
        return self.get_queryset().annotate(
            districts_count=Count("districts", distinct=True),
            circunscricoes_count=Count("districts__circunscricoes", distinct=True),
            polling_stations_count=Count(
                "districts__circunscricoes__polling_stations", distinct=True
            ),
            vote_tables_count=Count(
                "districts__circunscricoes__vote_tables", distinct=True
            ),
            total_voters=Sum("districts__circunscricoes__vote_tables__total_voters"),
        )

    def with_results(self):
        """Get countries with results preloaded"""
        return self.get_queryset().prefetch_related(
            "results_per_country_per_party__party"
        )

    def with_deputies(self):
        """Get countries with deputies preloaded"""
        return self.get_queryset().prefetch_related(
            "deputies_per_country_per_party__party"
        )

    def with_all_relations(self):
        """Get countries with all related data preloaded"""
        return self.get_queryset().prefetch_related(
            "districts",
            "districts__circunscricoes",
            "districts__circunscricoes__polling_stations",
            "districts__circunscricoes__vote_tables",
            "districts__circunscricoes__vote_tables__vote_entries",
            "districts__circunscricoes__vote_tables__vote_entries__party",
            "results_per_country_per_party__party",
            "deputies_per_country_per_party__party",
        )


class DistrictManager(models.Manager):
    """Custom manager for District model with optimized queries"""

    def get_queryset(self):
        return super().get_queryset().select_related("country")

    def with_country(self):
        """Get districts with country data preloaded"""
        return self.get_queryset().select_related("country")

    def with_circunscricao_counts(self):
        """Get districts with circunscricao counts"""
        return self.get_queryset().annotate(
            circunscricoes_count=Count("circunscricoes", distinct=True)
        )

    def with_vote_table_counts(self):
        """Get districts with vote table counts"""
        return self.get_queryset().annotate(
            vote_tables_count=Count("circunscricoes__vote_tables", distinct=True)
        )

    def with_full_stats(self):
        """Get districts with all statistics"""
        return self.get_queryset().annotate(
            circunscricoes_count=Count("circunscricoes", distinct=True),
            polling_stations_count=Count(
                "circunscricoes__polling_stations", distinct=True
            ),
            vote_tables_count=Count("circunscricoes__vote_tables", distinct=True),
            total_voters=Sum("circunscricoes__vote_tables__total_voters"),
        )

    def with_results(self):
        """Get districts with results preloaded"""
        return self.get_queryset().prefetch_related(
            "results_per_district_per_party__party"
        )

    def with_deputies(self):
        """Get districts with deputies preloaded"""
        return self.get_queryset().prefetch_related(
            "deputies_per_district_per_party__party"
        )

    def with_all_relations(self):
        """Get districts with all related data preloaded"""
        return (
            self.get_queryset()
            .select_related("country")
            .prefetch_related(
                "circunscricoes",
                "circunscricoes__polling_stations",
                "circunscricoes__vote_tables",
                "circunscricoes__vote_tables__vote_entries",
                "circunscricoes__vote_tables__vote_entries__party",
                "results_per_district_per_party__party",
                "deputies_per_district_per_party__party",
            )
        )

    def by_country(self, country_id):
        """Get districts by country"""
        return self.get_queryset().filter(country_id=country_id)

    def by_type(self, district_type):
        """Get districts by type"""
        return self.get_queryset().filter(district_type=district_type)


class CircunscricaoManager(models.Manager):
    """Custom manager for Circunscricao model with optimized queries"""

    def get_queryset(self):
        return super().get_queryset().select_related("district", "district__country")

    def with_district(self):
        """Get circunscricoes with district data preloaded"""
        return self.get_queryset().select_related("district", "district__country")

    def with_polling_station_counts(self):
        """Get circunscricoes with polling station counts"""
        return self.get_queryset().annotate(
            polling_stations_count=Count("polling_stations", distinct=True)
        )

    def with_vote_table_counts(self):
        """Get circunscricoes with vote table counts"""
        return self.get_queryset().annotate(
            vote_tables_count=Count("vote_tables", distinct=True)
        )

    def with_full_stats(self):
        """Get circunscricoes with all statistics"""
        return self.get_queryset().annotate(
            polling_stations_count=Count("polling_stations", distinct=True),
            vote_tables_count=Count("vote_tables", distinct=True),
            total_voters=Sum("vote_tables__total_voters"),
        )

    def with_results(self):
        """Get circunscricoes with results preloaded"""
        return self.get_queryset().prefetch_related(
            "results_per_circunscricao_per_party__party"
        )

    def with_all_relations(self):
        """Get circunscricoes with all related data preloaded"""
        return (
            self.get_queryset()
            .select_related("district", "district__country")
            .prefetch_related(
                "polling_stations",
                "vote_tables",
                "vote_tables__vote_entries",
                "vote_tables__vote_entries__party",
                "results_per_circunscricao_per_party__party",
            )
        )

    def by_district(self, district_id):
        """Get circunscricoes by district"""
        return self.get_queryset().filter(district_id=district_id)

    def with_vote_summary(self):
        """Get circunscricoes with vote summaries"""
        return self.get_queryset().annotate(
            total_valid_votes=Sum("vote_tables__valid_votes"),
            total_invalid_votes=Sum("vote_tables__invalid_votes"),
            total_blank_votes=Sum("vote_tables__blank_votes"),
            total_votes_cast=Sum("vote_tables__vote_entries__votes_count"),
        )


class PollingStationManager(models.Manager):
    """Custom manager for PollingStation model with optimized queries"""

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "circunscricao",
                "circunscricao__district",
                "circunscricao__district__country",
            )
        )

    def with_circunscricao(self):
        """Get polling stations with circunscricao data preloaded"""
        return self.get_queryset().select_related(
            "circunscricao",
            "circunscricao__district",
            "circunscricao__district__country",
        )

    def with_vote_table_counts(self):
        """Get polling stations with vote table counts"""
        return self.get_queryset().annotate(
            vote_tables_count=Count("vote_tables", distinct=True)
        )

    def with_full_stats(self):
        """Get polling stations with all statistics"""
        return self.get_queryset().annotate(
            vote_tables_count=Count("vote_tables", distinct=True),
            total_voters=Sum("vote_tables__total_voters"),
            total_votes_cast=Sum("vote_tables__vote_entries__votes_count"),
        )

    def with_all_relations(self):
        """Get polling stations with all related data preloaded"""
        return (
            self.get_queryset()
            .select_related(
                "circunscricao",
                "circunscricao__district",
                "circunscricao__district__country",
            )
            .prefetch_related(
                "vote_tables",
                "vote_tables__vote_entries",
                "vote_tables__vote_entries__party",
            )
        )

    def by_circunscricao(self, circunscricao_id):
        """Get polling stations by circunscricao"""
        return self.get_queryset().filter(circunscricao_id=circunscricao_id)


class PartyManager(models.Manager):
    """Custom manager for Party model with optimized queries"""

    def get_queryset(self):
        return super().get_queryset()

    def active(self):
        """Get only active parties"""
        return self.get_queryset().filter(is_active=True)

    def with_vote_counts(self):
        """Get parties with vote counts"""
        return self.get_queryset().annotate(
            vote_entries_count=Count("vote_entries", distinct=True),
            total_votes=Sum("vote_entries__votes_count"),
        )

    def with_results(self):
        """Get parties with results preloaded"""
        return self.get_queryset().prefetch_related(
            "results_per_country_per_party",
            "results_per_district_per_party",
            "results_per_circunscricao_per_party",
        )

    def with_deputies(self):
        """Get parties with deputies preloaded"""
        return self.get_queryset().prefetch_related(
            "deputies_per_country_per_party", "deputies_per_district_per_party"
        )

    def with_all_relations(self):
        """Get parties with all related data preloaded"""
        return self.get_queryset().prefetch_related(
            "vote_entries",
            "vote_entries__vote_table",
            "vote_entries__vote_table__circunscricao",
            "results_per_country_per_party",
            "results_per_district_per_party",
            "results_per_circunscricao_per_party",
            "deputies_per_country_per_party",
            "deputies_per_district_per_party",
        )

    def get_by_abbreviation(self, abbreviation):
        """Get party by abbreviation"""
        return self.get_queryset().filter(abbreviation=abbreviation).first()


class VoteTableManager(models.Manager):
    """Custom manager for VoteTable model with optimized queries"""

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "circunscricao",
                "circunscricao__district",
                "circunscricao__district__country",
                "polling_station",
            )
        )

    def with_circunscricao(self):
        """Get vote tables with circunscricao data preloaded"""
        return self.get_queryset().select_related(
            "circunscricao",
            "circunscricao__district",
            "circunscricao__district__country",
            "polling_station",
        )

    def with_vote_entries(self):
        """Get vote tables with vote entries preloaded"""
        return self.get_queryset().prefetch_related(
            "vote_entries", "vote_entries__party"
        )

    def with_full_stats(self):
        """Get vote tables with all statistics"""
        return self.get_queryset().annotate(
            total_votes_cast=Sum("vote_entries__votes_count")
        )

    def with_all_relations(self):
        """Get vote tables with all related data preloaded"""
        return (
            self.get_queryset()
            .select_related(
                "circunscricao",
                "circunscricao__district",
                "circunscricao__district__country",
                "polling_station",
            )
            .prefetch_related("vote_entries", "vote_entries__party")
        )

    def by_circunscricao(self, circunscricao_id):
        """Get vote tables by circunscricao"""
        return self.get_queryset().filter(circunscricao_id=circunscricao_id)

    def by_district(self, district_id):
        """Get vote tables by district"""
        return self.get_queryset().filter(circunscricao__district_id=district_id)

    def with_turnout(self):
        """Get vote tables with turnout calculation"""
        return self.get_queryset().annotate(
            total_votes_cast=Sum("vote_entries__votes_count")
        )

    def get_summary(self):
        """Get summary statistics for all vote tables"""
        return self.get_queryset().aggregate(
            total_voters=Sum("total_voters"),
            total_valid_votes=Sum("valid_votes"),
            total_invalid_votes=Sum("invalid_votes"),
            total_blank_votes=Sum("blank_votes"),
            total_votes_cast=Sum("vote_entries__votes_count"),
            avg_turnout=Avg("vote_entries__votes_count") / Avg("total_voters") * 100,
            max_voters=Max("total_voters"),
            min_voters=Min("total_voters"),
        )


class VoteEntryManager(models.Manager):
    """Custom manager for VoteEntry model with optimized queries"""

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "vote_table",
                "vote_table__circunscricao",
                "vote_table__circunscricao__district",
                "vote_table__circunscricao__district__country",
                "vote_table__polling_station",
                "party",
            )
        )

    def with_vote_table(self):
        """Get vote entries with vote table data preloaded"""
        return self.get_queryset().select_related(
            "vote_table",
            "vote_table__circunscricao",
            "vote_table__polling_station",
            "party",
        )

    def with_all_relations(self):
        """Get vote entries with all related data preloaded"""
        return self.get_queryset().select_related(
            "vote_table",
            "vote_table__circunscricao",
            "vote_table__circunscricao__district",
            "vote_table__circunscricao__district__country",
            "vote_table__polling_station",
            "party",
        )

    def by_vote_table(self, vote_table_id):
        """Get vote entries by vote table"""
        return self.get_queryset().filter(vote_table_id=vote_table_id)

    def by_party(self, party_id):
        """Get vote entries by party"""
        return self.get_queryset().filter(party_id=party_id)

    def by_circunscricao(self, circunscricao_id):
        """Get vote entries by circunscricao"""
        return self.get_queryset().filter(vote_table__circunscricao_id=circunscricao_id)

    def by_district(self, district_id):
        """Get vote entries by district"""
        return self.get_queryset().filter(
            vote_table__circunscricao__district_id=district_id
        )

    def by_country(self, country_id):
        """Get vote entries by country"""
        return self.get_queryset().filter(
            vote_table__circunscricao__district__country_id=country_id
        )

    def with_party_totals(self):
        """Get vote entries with party totals"""
        return (
            self.get_queryset()
            .values("party_id", "party__name", "party__abbreviation", "party__color")
            .annotate(total_votes=Sum("votes_count"))
            .order_by("-total_votes")
        )


class ResultPerCountryPerPartyManager(models.Manager):
    """Custom manager for ResultPerCountryPerParty model"""

    def get_queryset(self):
        return super().get_queryset().select_related("country", "party")

    def with_all_relations(self):
        """Get results with all related data preloaded"""
        return self.get_queryset().select_related("country", "party")

    def by_country(self, country_id):
        """Get results by country"""
        return self.get_queryset().filter(country_id=country_id)


class ResultPerDistrictPerPartyManager(models.Manager):
    """Custom manager for ResultPerDistrictPerParty model"""

    def get_queryset(self):
        return super().get_queryset().select_related("district", "party")

    def with_all_relations(self):
        """Get results with all related data preloaded"""
        return self.get_queryset().select_related("district", "party")

    def by_district(self, district_id):
        """Get results by district"""
        return self.get_queryset().filter(district_id=district_id)


class ResultPerCircunscricaoPerPartyManager(models.Manager):
    """Custom manager for ResultPerCircunscricaoPerParty model"""

    def get_queryset(self):
        return super().get_queryset().select_related("circunscricao", "party")

    def with_all_relations(self):
        """Get results with all related data preloaded"""
        return self.get_queryset().select_related("circunscricao", "party")

    def by_circunscricao(self, circunscricao_id):
        """Get results by circunscricao"""
        return self.get_queryset().filter(circunscricao_id=circunscricao_id)


class DeputiesPerCountryPerPartyManager(models.Manager):
    """Custom manager for DeputiesPerCountryPerParty model"""

    def get_queryset(self):
        return super().get_queryset().select_related("country", "party")

    def with_all_relations(self):
        """Get deputies with all related data preloaded"""
        return self.get_queryset().select_related("country", "party")

    def by_country(self, country_id):
        """Get deputies by country"""
        return self.get_queryset().filter(country_id=country_id)


class DeputiesPerDistrictPerPartyManager(models.Manager):
    """Custom manager for DeputiesPerDistrictPerParty model"""

    def get_queryset(self):
        return super().get_queryset().select_related("district", "party")

    def with_all_relations(self):
        """Get deputies with all related data preloaded"""
        return self.get_queryset().select_related("district", "party")

    def by_district(self, district_id):
        """Get deputies by district"""
        return self.get_queryset().filter(district_id=district_id)


# ============================================
# UPDATED MODELS WITH CUSTOM MANAGERS
# ============================================


class Agent(models.Model):
    """
    Customer profile model that links to the user model via OneToOneField.
    This is the ONLY model that directly links to the user model.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AgentManager()

    def __str__(self):
        return f"Agent {self.user.first_name} {self.user.last_name}"


class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    total_deputies = models.PositiveIntegerField(default=55)

    objects = CountryManager()

    class Meta:
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name


class District(models.Model):
    name = models.CharField(max_length=100)
    sigla = models.CharField(max_length=10)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="districts"
    )
    total_deputies = models.PositiveIntegerField(default=0)
    DISTRIC_TYPE_CHOICES = [
        ("SAO_TOME", "São Tomé e Príncipe"),
        ("DIASPORA_EUROPE", "Diaspora Europa"),
        ("DIASPORA_AFRICA", "Diaspora Africa"),
    ]
    district_type = models.CharField(
        max_length=20, choices=DISTRIC_TYPE_CHOICES, default="SAO_TOME"
    )

    objects = DistrictManager()

    class Meta:
        unique_together = ["name", "sigla", "country"]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.sigla})"


class Circunscricao(models.Model):
    code = models.CharField(max_length=20, unique=True)
    district = models.ForeignKey(
        District, on_delete=models.CASCADE, related_name="circunscricoes"
    )
    name = models.CharField(max_length=100, blank=True, null=True)

    objects = CircunscricaoManager()

    class Meta:
        verbose_name_plural = "Circunscrições"
        ordering = ["code"]

    def __str__(self):
        return self.code


class PollingStation(models.Model):
    name = models.CharField(max_length=200)
    circunscricao = models.ForeignKey(
        Circunscricao, on_delete=models.CASCADE, related_name="polling_stations"
    )

    objects = PollingStationManager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Party(models.Model):
    name = models.CharField(max_length=100, unique=True)
    abbreviation = models.CharField(max_length=20, unique=True)
    color = models.CharField(max_length=7, default="#000000")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PartyManager()

    class Meta:
        verbose_name_plural = "Parties"
        ordering = ["name"]

    def __str__(self):
        return f"{self.abbreviation} - {self.name}"


class VoteTable(models.Model):
    code = models.CharField(max_length=20)
    circunscricao = models.ForeignKey(
        Circunscricao, on_delete=models.CASCADE, related_name="vote_tables"
    )
    polling_station = models.ForeignKey(
        PollingStation, on_delete=models.CASCADE, related_name="vote_tables"
    )
    total_voters = models.PositiveIntegerField(default=0, verbose_name="Eleitores")
    valid_votes = models.PositiveIntegerField(default=0)
    invalid_votes = models.PositiveIntegerField(default=0)
    blank_votes = models.PositiveIntegerField(default=0)
    location_details = models.TextField(blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = VoteTableManager()

    class Meta:
        unique_together = ["code", "circunscricao"]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.circunscricao.code}"


class VoteEntry(models.Model):
    vote_table = models.ForeignKey(
        VoteTable, on_delete=models.CASCADE, related_name="vote_entries"
    )
    party = models.ForeignKey(
        Party, on_delete=models.CASCADE, related_name="vote_entries"
    )
    votes_count = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0)]
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = VoteEntryManager()

    class Meta:
        unique_together = ["vote_table", "party"]
        ordering = ["vote_table", "party"]

    def __str__(self):
        return f"{self.vote_table.code} - {self.party.abbreviation}: {self.votes_count}"


class ResultPerCountryPerParty(models.Model):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="results_per_country_per_party",
        null=True,
        blank=True,
    )
    party = models.ForeignKey(
        Party, on_delete=models.CASCADE, related_name="results_per_country_per_party"
    )
    result = models.IntegerField()
    deputies = models.IntegerField()
    objects = ResultPerCountryPerPartyManager()

    class Meta:
        unique_together = ["country", "party"]


class ResultPerDistrictPerParty(models.Model):
    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        related_name="results_per_district_per_party",
        null=True,
        blank=True,
    )
    party = models.ForeignKey(
        Party, on_delete=models.CASCADE, related_name="results_per_district_per_party"
    )
    result = models.IntegerField()
    deputies = models.IntegerField()

    objects = ResultPerDistrictPerPartyManager()

    class Meta:
        unique_together = ["district", "party"]


class ResultPerCircunscricaoPerParty(models.Model):
    circunscricao = models.ForeignKey(
        Circunscricao,
        on_delete=models.CASCADE,
        related_name="results_per_circunscricao_per_party",
        null=True,
        blank=True,
    )
    party = models.ForeignKey(
        Party,
        on_delete=models.CASCADE,
        related_name="results_per_circunscricao_per_party",
    )
    result = models.IntegerField()

    objects = ResultPerCircunscricaoPerPartyManager()
    deputies = models.IntegerField(default=0)

    class Meta:
        unique_together = ["circunscricao", "party"]
