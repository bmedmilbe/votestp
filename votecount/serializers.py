from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from .models import (
    Agent,
    Circunscricao,
    Country,
    District,
    Party,
    PollingStation,
    ResultPerCircunscricaoPerParty,
    ResultPerCountryPerParty,
    ResultPerDistrictPerParty,
    VoteEntry,
    VoteTable,
)
from .tasks import sum_vote_entry_task

# ============================================
# BASE SERIALIZERS
# ============================================

class AgentSerializer(serializers.ModelSerializer):
    """Serializer for Agent model"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Agent
        fields = ['id', 'user', 'user_email', 'user_full_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


class CountrySerializer(serializers.ModelSerializer):
    """Serializer for Country model"""
    districts_count = serializers.IntegerField(read_only=True)
    vote_tables_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Country
        fields = ['id', 'name', 'code', 'total_deputies', 'districts_count', 'vote_tables_count']
        read_only_fields = ['id']
    
    def get_vote_tables_count(self, obj):
        return VoteTable.objects.filter(circunscricao__district__country=obj).count()


class DistrictSerializer(serializers.ModelSerializer):
    """Serializer for District model"""
    country_name = serializers.CharField(source='country.name', read_only=True)
    country_code = serializers.CharField(source='country.code', read_only=True)
    circunscricoes_count = serializers.IntegerField(read_only=True)
    vote_tables_count = serializers.SerializerMethodField()
    
    class Meta:
        model = District
        fields = ['id', 'name', 'sigla', 'country', 'country_name', 'country_code',
                  'total_deputies', 'district_type', 'circunscricoes_count', 
                  'vote_tables_count']
        read_only_fields = ['id']
    
    def get_vote_tables_count(self, obj):
        return VoteTable.objects.filter(circunscricao__district=obj).count()


class CircunscricaoSerializer(serializers.ModelSerializer):
    """Serializer for Circunscricao model"""
    district_name = serializers.CharField(source='district.name', read_only=True)
    district_sigla = serializers.CharField(source='district.sigla', read_only=True)
    country_name = serializers.CharField(source='district.country.name', read_only=True)
    polling_stations_count = serializers.IntegerField(read_only=True)
    vote_tables_count = serializers.IntegerField(read_only=True)
    total_voters = serializers.SerializerMethodField()
    
    class Meta:
        model = Circunscricao
        fields = ['id', 'code', 'name', 'district', 'district_name', 'district_sigla',
                  'country_name', 'polling_stations_count', 'vote_tables_count', 
                  'total_voters']
        read_only_fields = ['id']
    
    def get_total_voters(self, obj):
        return obj.vote_tables.aggregate(total=Sum('total_voters'))['total'] or 0


class PollingStationSerializer(serializers.ModelSerializer):
    """Serializer for PollingStation model"""
    circunscricao_code = serializers.CharField(source='circunscricao.code', read_only=True)
    circunscricao_name = serializers.CharField(source='circunscricao.name', read_only=True)
    district_name = serializers.CharField(source='circunscricao.district.name', read_only=True)
    country_name = serializers.CharField(source='circunscricao.district.country.name', read_only=True)
    vote_tables_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = PollingStation
        fields = ['id', 'name', 'circunscricao', 'circunscricao_code', 
                  'circunscricao_name', 'district_name', 'country_name',
                  'vote_tables_count']
        read_only_fields = ['id']


class PartySerializer(serializers.ModelSerializer):
    """Serializer for Party model"""
    vote_entries_count = serializers.IntegerField(read_only=True)
    total_votes = serializers.SerializerMethodField()
    
    class Meta:
        model = Party
        fields = ['id', 'name', 'abbreviation', 'color', 'is_active', 
                  'created_at', 'updated_at', 'vote_entries_count', 'total_votes']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_votes(self, obj):
        return obj.vote_entries.aggregate(total=Sum('votes_count'))['total'] or 0


# ============================================
# VOTE TABLE AND VOTE ENTRY SERIALIZERS
# ============================================

class VoteEntrySerializer(serializers.ModelSerializer):
    """Serializer for VoteEntry model"""
    party_name = serializers.CharField(source='party.name', read_only=True)
    party_abbreviation = serializers.CharField(source='party.abbreviation', read_only=True)
    party_color = serializers.CharField(source='party.color', read_only=True)
    vote_table_code = serializers.CharField(source='vote_table.code', read_only=True)
    circunscricao_code = serializers.CharField(
        source='vote_table.circunscricao.code', read_only=True
    )
    
    class Meta:
        model = VoteEntry
        fields = ['id', 'vote_table', 'vote_table_code', 'circunscricao_code',
                  'party', 'party_name', 'party_abbreviation', 'party_color',
                  'votes_count', 'recorded_at', 'updated_at']
        read_only_fields = ['id', 'recorded_at', 'updated_at']

class VoteEntryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating or updating VoteEntry models via nested routes"""
    
    class Meta:
        model = VoteEntry
        fields = ['id', 'vote_table', 'party', 'votes_count']
        read_only_fields = ['id', 'vote_table', 'recorded_at', 'updated_at']
        validators = []
    def create(self, validated_data):
        vote_table_pk = self.context["vote_table_pk"]
        party = validated_data.pop('party')

        with transaction.atomic():
            vote_entry, created = VoteEntry.objects.update_or_create(
                vote_table_id=vote_table_pk,
                party=party,
                defaults=validated_data
            )
            
            # transaction.on_commit(lambda: sum_vote_entry_task.delay(vote_entry.id))
            transaction.on_commit(lambda: sum_vote_entry_task(vote_entry.id))
            
        return vote_entry
            
    
class VoteTableSerializer(serializers.ModelSerializer):
    """Serializer for VoteTable model"""
    circunscricao_code = serializers.CharField(source='circunscricao.code', read_only=True)
    circunscricao_name = serializers.CharField(source='circunscricao.name', read_only=True)
    polling_station_name = serializers.CharField(source='polling_station.name', read_only=True)
    district_name = serializers.CharField(
        source='circunscricao.district.name', read_only=True
    )
    country_name = serializers.CharField(
        source='circunscricao.district.country.name', read_only=True
    )
    vote_entries = VoteEntrySerializer(many=True, read_only=True)
    total_votes_cast = serializers.SerializerMethodField()
    turnout_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = VoteTable
        fields = ['id', 'code', 'circunscricao', 'circunscricao_code', 
                  'circunscricao_name', 'polling_station', 'polling_station_name',
                  'district_name', 'country_name', 'total_voters', 'valid_votes',
                  'invalid_votes', 'blank_votes', 'location_details', 
                  'recorded_at', 'updated_at', 'vote_entries', 
                  'total_votes_cast', 'turnout_percentage']
        read_only_fields = ['id', 'recorded_at', 'updated_at']
    
    def get_total_votes_cast(self, obj):
        return obj.vote_entries.aggregate(total=Sum('votes_count'))['total'] or 0
    
    def get_turnout_percentage(self, obj):
        total_votes = obj.vote_entries.aggregate(total=Sum('votes_count'))['total'] or 0
        if obj.total_voters > 0:
            return round((total_votes / obj.total_voters) * 100, 2)
        return 0.0


class VoteTableCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating VoteTable"""
    vote_entries = VoteEntryCreateSerializer(many=True)
    class Meta:
        model = VoteTable
        fields = ['id',  'invalid_votes', 'blank_votes', 'vote_entries']
        read_only_fields = ['id']

    def update(self, instance, validated_data):
        
        instance.invalid_votes = validated_data.get('invalid_votes', instance.invalid_votes)
        instance.blank_votes = validated_data.get('blank_votes', instance.blank_votes)
        instance.save()
        parties_data = validated_data.pop('vote_entries')
        for party_data in parties_data:
            party = party_data.pop('party')
            
            with transaction.atomic():
                vote_entry, created = VoteEntry.objects.update_or_create(
                    vote_table=instance,
                    party=party,
                    defaults=party_data
                )
                
                # transaction.on_commit(lambda: sum_vote_entry_task.delay(vote_entry.id))
                transaction.on_commit(lambda: sum_vote_entry_task(vote_entry.id))
                        
            # VoteEntry.objects.create(election_result=election_result, **party_data)
       
        return instance

    
    
# ============================================
# RESULT AND DEPUTIES SERIALIZERS
# ============================================

class ResultPerPartySerializer(serializers.ModelSerializer):
    """Serializer for results per party"""
    party_id = serializers.IntegerField(source='party.id', read_only=True)
    party_name = serializers.CharField(source='party.name', read_only=True)
    party_abbreviation = serializers.CharField(source='party.abbreviation', read_only=True)
    party_color = serializers.CharField(source='party.color', read_only=True)
    
    class Meta:
        model = ResultPerCountryPerParty  # Works for all Result models
        fields = ['id', 'party_id', 'party_name', 'party_abbreviation', 
                  'party_color', 'result', 'deputies']


# ============================================
# NESTED SERIALIZERS FOR COMPLEX RESPONSES
# ============================================

class NestedVoteEntrySerializer(serializers.ModelSerializer):
    """Nested VoteEntry serializer for detailed responses"""
    party = PartySerializer(read_only=True)
    
    class Meta:
        model = VoteEntry
        fields = ['id', 'party', 'votes_count', 'recorded_at']
        read_only_fields = ['id', 'recorded_at']


class NestedVoteTableSerializer(serializers.ModelSerializer):
    """Nested VoteTable serializer with vote entries"""
    vote_entries = NestedVoteEntrySerializer(many=True, read_only=True)
    circunscricao_code = serializers.CharField(source='circunscricao.code', read_only=True)
    polling_station_name = serializers.CharField(source='polling_station.name', read_only=True)
    total_votes_cast = serializers.SerializerMethodField()
    turnout_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = VoteTable
        fields = ['id', 'code', 'circunscricao_code', 'polling_station_name',
                  'total_voters', 'valid_votes', 'invalid_votes', 'blank_votes',
                  'location_details', 'recorded_at', 'vote_entries',
                  'total_votes_cast', 'turnout_percentage']
    
    def get_total_votes_cast(self, obj):
        return obj.vote_entries.aggregate(total=Sum('votes_count'))['total'] or 0
    
    def get_turnout_percentage(self, obj):
        total_votes = obj.vote_entries.aggregate(total=Sum('votes_count'))['total'] or 0
        if obj.total_voters > 0:
            return round((total_votes / obj.total_voters) * 100, 2)
        return 0.0


class NestedCircunscricaoSerializer(serializers.ModelSerializer):
    """Nested Circunscricao serializer with vote tables and results"""
    vote_tables = NestedVoteTableSerializer(many=True, read_only=True)
    results = serializers.SerializerMethodField()
    district_name = serializers.CharField(source='district.name', read_only=True)
    total_voters = serializers.SerializerMethodField()
    
    class Meta:
        model = Circunscricao
        fields = ['id', 'code', 'name', 'district_name', 'vote_tables', 
                  'results', 'total_voters']
    
    def get_results(self, obj):
        results = ResultPerCircunscricaoPerParty.objects.filter(
            circunscricao=obj
        ).select_related('party')
        return ResultPerPartySerializer(results, many=True).data
    
    def get_total_voters(self, obj):
        return obj.vote_tables.aggregate(total=Sum('total_voters'))['total'] or 0


class NestedDistrictSerializer(serializers.ModelSerializer):
    """Nested District serializer with circunscricoes, vote tables, results and deputies"""
    circunscricoes = NestedCircunscricaoSerializer(many=True, read_only=True)
    vote_tables = serializers.SerializerMethodField()
    results = serializers.SerializerMethodField()
    deputies = serializers.SerializerMethodField()
    country_name = serializers.CharField(source='country.name', read_only=True)
    total_voters = serializers.SerializerMethodField()
    
    class Meta:
        model = District
        fields = ['id', 'name', 'sigla', 'country_name', 'total_deputies', 
                  'district_type', 'circunscricoes', 'vote_tables', 'results', 
                  'deputies', 'total_voters']
    
    def get_vote_tables(self, obj):
        vote_tables = VoteTable.objects.filter(circunscricao__district=obj)
        return NestedVoteTableSerializer(vote_tables, many=True).data
    
    def get_results(self, obj):
        results = ResultPerDistrictPerParty.objects.filter(
            district=obj
        ).select_related('party')
        return ResultPerPartySerializer(results, many=True).data
    
    def get_deputies(self, obj):
            deputies = ResultPerDistrictPerParty.objects.filter(
                district=obj
            ).select_related('party')
            return ResultPerPartySerializer(deputies, many=True).data
    
    def get_total_voters(self, obj):
        return VoteTable.objects.filter(
            circunscricao__district=obj
        ).aggregate(total=Sum('total_voters'))['total'] or 0


class NestedCountrySerializer(serializers.ModelSerializer):
    """Nested Country serializer with districts, results and deputies"""
    districts = NestedDistrictSerializer(many=True, read_only=True)
    results = serializers.SerializerMethodField()
    deputies = serializers.SerializerMethodField()
    total_voters = serializers.SerializerMethodField()
    
    class Meta:
        model = Country
        fields = ['id', 'name', 'code', 'total_deputies', 'districts', 
                  'results', 'deputies', 'total_voters']
    
    def get_results(self, obj):
        results = ResultPerCountryPerParty.objects.filter(
            country=obj
        ).select_related('party')
        return ResultPerPartySerializer(results, many=True).data
    
    def get_deputies(self, obj):
        deputies = ResultPerCountryPerParty.objects.filter(
            country=obj
        ).select_related('party')
        return ResultPerPartySerializer(deputies, many=True).data
    
    def get_total_voters(self, obj):
        return VoteTable.objects.filter(
            circunscricao__district__country=obj
        ).aggregate(total=Sum('total_voters'))['total'] or 0


# ============================================
# SUMMARY AND AGGREGATION SERIALIZERS
# ============================================

class VoteTableSummarySerializer(serializers.Serializer):
    """Serializer for vote table summary"""
    code = serializers.CharField()
    total_voters = serializers.IntegerField()
    valid_votes = serializers.IntegerField()
    invalid_votes = serializers.IntegerField()
    blank_votes = serializers.IntegerField()
    total_votes_cast = serializers.IntegerField()
    turnout_percentage = serializers.FloatField()
    circunscricao = serializers.CharField()
    polling_station = serializers.CharField()


class CountrySummarySerializer(serializers.Serializer):
    """Serializer for country summary"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()
    total_deputies = serializers.IntegerField()
    total_districts = serializers.IntegerField()
    total_circunscricoes = serializers.IntegerField()
    total_vote_tables = serializers.IntegerField()
    total_voters = serializers.IntegerField()
    total_votes_cast = serializers.IntegerField()
    turnout_percentage = serializers.FloatField()


class PartyResultsSerializer(serializers.Serializer):
    """Serializer for party results aggregation"""
    party_id = serializers.IntegerField()
    party_name = serializers.CharField()
    party_abbreviation = serializers.CharField()
    party_color = serializers.CharField()
    total_votes = serializers.IntegerField()
    percentage = serializers.FloatField()
    deputies = serializers.IntegerField()


class ElectionResultsSerializer(serializers.Serializer):
    """Serializer for complete election results"""
    total_voters = serializers.IntegerField()
    total_votes_cast = serializers.IntegerField()
    turnout_percentage = serializers.FloatField()
    valid_votes = serializers.IntegerField()
    invalid_votes = serializers.IntegerField()
    blank_votes = serializers.IntegerField()
    results_by_party = PartyResultsSerializer(many=True)
    last_updated = serializers.DateTimeField()


# ============================================
# DYNAMIC SERIALIZER FOR FLEXIBLE RESPONSES
# ============================================

class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """
    
    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)
        
        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)
        
        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class FlexibleCountrySerializer(DynamicFieldsModelSerializer):
    """Flexible Country serializer with dynamic fields"""
    
    class Meta:
        model = Country
        fields = '__all__'


class FlexibleDistrictSerializer(DynamicFieldsModelSerializer):
    """Flexible District serializer with dynamic fields"""
    country_name = serializers.CharField(source='country.name', read_only=True)
    
    class Meta:
        model = District
        fields = '__all__'


class FlexibleVoteTableSerializer(DynamicFieldsModelSerializer):
    """Flexible VoteTable serializer with dynamic fields"""
    circunscricao_code = serializers.CharField(source='circunscricao.code', read_only=True)
    polling_station_name = serializers.CharField(source='polling_station.name', read_only=True)
    
    class Meta:
        model = VoteTable
        fields = '__all__'