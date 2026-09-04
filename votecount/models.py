
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum


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

    def __str__(self):
        return f"Agent {self.user.first_name} {self.user.last_name}"



class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    total_deputies = models.PositiveIntegerField(default=55)
    
    class Meta:
        verbose_name_plural = "Countries"
    
    def __str__(self):
        return self.name

class District(models.Model):
    name = models.CharField(max_length=100)
    sigla = models.CharField(max_length=10)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='districts')
    total_deputies = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['name', 'sigla', 'country']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.sigla})"

class Circunscricao(models.Model):
    code = models.CharField(max_length=20, unique=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='circunscricoes')
    name = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Circunscrições"
        ordering = ['code']
    
    def __str__(self):
        return self.code

class PollingStation(models.Model):
    name = models.CharField(max_length=200)
    circunscricao = models.ForeignKey(Circunscricao, on_delete=models.CASCADE, related_name='polling_stations')
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Party(models.Model):
    name = models.CharField(max_length=100, unique=True)
    abbreviation = models.CharField(max_length=20, unique=True)
    color = models.CharField(max_length=7, default='#000000')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Parties"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.abbreviation} - {self.name}"

class VoteTable(models.Model):
    code = models.CharField(max_length=20)
    circunscricao = models.ForeignKey(Circunscricao, on_delete=models.CASCADE, related_name='vote_tables')
    polling_station = models.ForeignKey(PollingStation, on_delete=models.CASCADE, related_name='vote_tables')
    total_voters = models.PositiveIntegerField(default=0, verbose_name="Eleitores")
    valid_votes = models.PositiveIntegerField(default=0)
    invalid_votes = models.PositiveIntegerField(default=0)
    blank_votes = models.PositiveIntegerField(default=0)
    location_details = models.TextField(blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['code', 'circunscricao']
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.circunscricao.code}"
    
    def calculate_total_votes(self):
        resultado = self.vote_entries.aggregate(total=Sum('votes_count'))
        return resultado['total'] or 0
    
    def save(self, *args, **kwargs):
        self.valid_votes = self.calculate_total_votes()
        super().save(*args, **kwargs)

class VoteEntry(models.Model):
    vote_table = models.ForeignKey(VoteTable, on_delete=models.CASCADE, related_name='vote_entries')
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='vote_entries')
    votes_count = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['vote_table', 'party']
        ordering = ['vote_table', 'party']
    
    def __str__(self):
        return f"{self.vote_table.code} - {self.party.abbreviation}: {self.votes_count}"

class VoteResult(models.Model):
    RESULT_TYPE_CHOICES = [
        ('TABLE', 'Voting Table'),
        ('CIRCUNSCRICAO', 'Circunscrição'),
        ('DISTRICT', 'District'),
        ('COUNTRY', 'Country'),
    ]
    
    result_type = models.CharField(max_length=20, choices=RESULT_TYPE_CHOICES)
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='results')
    circunscricao = models.ForeignKey(Circunscricao, on_delete=models.CASCADE, related_name='results', null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='results', null=True, blank=True)
    vote_table = models.ForeignKey(VoteTable, on_delete=models.CASCADE, related_name='results', null=True, blank=True)
    total_votes = models.PositiveIntegerField(default=0)
    deputies_allocated = models.PositiveIntegerField(default=0)
    calculated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['result_type', 'party', 'circunscricao', 'district', 'vote_table']
    
    def __str__(self):
        return f"{self.result_type} - {self.party.abbreviation}: {self.total_votes}"

class HondtCalculation(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='hondt_calculations')
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='hondt_calculations')
    total_votes = models.PositiveIntegerField(default=0)
    deputies_allocated = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    calculation_round = models.PositiveIntegerField(default=1)
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['district', 'party', 'calculation_round']
        ordering = ['district', 'party', 'calculation_round']
    
    def __str__(self):
        return f"{self.district.name} - {self.party.abbreviation}: {self.deputies_allocated} deputies"

class ElectionStats(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='election_stats')
    total_voters = models.PositiveIntegerField(default=0)
    total_valid_votes = models.PositiveIntegerField(default=0)
    total_invalid_votes = models.PositiveIntegerField(default=0)
    total_blank_votes = models.PositiveIntegerField(default=0)
    voter_turnout = models.FloatField(default=0.0)
    total_deputies = models.PositiveIntegerField(default=55)
    calculated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Election Statistics"
    
    def __str__(self):
        return f"Election Stats - {self.country.name}"

class OriginalDataImport(models.Model):
    json_data = models.JSONField()
    import_date = models.DateTimeField(auto_now_add=True)
    imported_by = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Import at {self.import_date.strftime('%Y-%m-%d %H:%M')}"







    
