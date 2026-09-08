
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


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
    DISTRIC_TYPE_CHOICES = [
        ('SAO TOME', 'São Tomé e Príncipe'),
        ('DIASPORA_EUROPE', 'Diaspora Europa'),
        ('DIASPORA_AFRICA', 'Diaspora Africa'),
    ]
            
    district_type = models.CharField(max_length=20, choices=DISTRIC_TYPE_CHOICES, default='SAO TOME')
          
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

class ResultPerCountryPerParty(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='results_per_country_per_party', null=True, blank=True)
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='results_per_country_per_party')
    result = models.IntegerField()

    class Meta:
        unique_together = ['country', 'party']

class ResultPerDistrictPerParty(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='results_per_district_per_party', null=True, blank=True)
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='results_per_district_per_party')
    result = models.IntegerField()

    class Meta:
        unique_together = ['district', 'party']

class ResultPerCircunscricaoPerParty(models.Model):
    circunscricao = models.ForeignKey(Circunscricao, on_delete=models.CASCADE, related_name='results_per_circunscricao_per_party', null=True, blank=True)
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='results_per_circunscricao_per_party')
    result = models.IntegerField()

    class Meta:
        unique_together = ['circunscricao', 'party']


class DeputiesPerCountryPerParty(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='deputies_per_country_per_party', null=True, blank=True)
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='deputies_per_country_per_party')
    deputies = models.IntegerField()

    class Meta:
        unique_together = ['country', 'party']
class DeputiesPerDistrictPerParty(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='deputies_per_district_per_party', null=True, blank=True)
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='deputies_per_district_per_party')
    deputies = models.IntegerField()

    class Meta:
        unique_together = ['district', 'party']



    




    
