from django.db.models import Sum
from rest_framework import serializers

from .models import (
    Agent,
    Circunscricao,
    Country,
    District,
    ElectionStats,
    HondtCalculation,
    OriginalDataImport,
    Party,
    PollingStation,
    VoteEntry,
    VoteResult,
    VoteTable,
)

# ============================================
# SERIALIZERS BÁSICOS
# ============================================

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'code', 'total_deputies']
        read_only_fields = ['id']


class DistrictSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source='country.name', read_only=True)
    country_code = serializers.CharField(source='country.code', read_only=True)
    
    class Meta:
        model = District
        fields = ['id', 'name', 'sigla', 'country', 'country_name', 'country_code', 'total_deputies']
        read_only_fields = ['id']


class CircunscricaoSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source='district.name', read_only=True)
    district_sigla = serializers.CharField(source='district.sigla', read_only=True)
    
    class Meta:
        model = Circunscricao
        fields = ['id', 'code', 'name', 'district', 'district_name', 'district_sigla']
        read_only_fields = ['id']


class PollingStationSerializer(serializers.ModelSerializer):
    circunscricao_code = serializers.CharField(source='circunscricao.code', read_only=True)
    
    class Meta:
        model = PollingStation
        fields = ['id', 'name', 'circunscricao', 'circunscricao_code']
        read_only_fields = ['id']


class PartySerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = ['id', 'name', 'abbreviation', 'color', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================
# SERIALIZERS PARA VOTE TABLE E ENTRIES
# ============================================

class VoteEntrySerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source='party.name', read_only=True)
    party_abbreviation = serializers.CharField(source='party.abbreviation', read_only=True)
    party_color = serializers.CharField(source='party.color', read_only=True)
    percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = VoteEntry
        fields = [
            'id', 'vote_table', 'party', 'party_name', 'party_abbreviation', 
            'party_color', 'votes_count', 'percentage', 'recorded_at', 'updated_at'
        ]
        read_only_fields = ['id', 'recorded_at', 'updated_at']
    
    def get_percentage(self, obj):
        """Calcular percentagem de votos para este partido na mesa"""
        vote_table = obj.vote_table
        if vote_table and vote_table.valid_votes > 0:
            return round((obj.votes_count / vote_table.valid_votes) * 100, 2)
        return 0.0


class VoteEntryCreateSerializer(serializers.Serializer):
    """Serializer para criar/atualizar entradas de voto"""
    party_abbreviation = serializers.CharField(max_length=20)
    votes = serializers.IntegerField(min_value=0)
    
    def validate_votes(self, value):
        if value < 0:
            raise serializers.ValidationError("Votes cannot be negative")
        return value


class VoteTableSerializer(serializers.ModelSerializer):
    circunscricao_code = serializers.CharField(source='circunscricao.code', read_only=True)
    circunscricao_name = serializers.CharField(source='circunscricao.name', read_only=True)
    polling_station_name = serializers.CharField(source='polling_station.name', read_only=True)
    vote_entries = VoteEntrySerializer(many=True, read_only=True)
    total_valid_votes = serializers.SerializerMethodField()
    voter_turnout = serializers.SerializerMethodField()
    
    class Meta:
        model = VoteTable
        fields = [
            'id', 'code', 'circunscricao', 'circunscricao_code', 'circunscricao_name',
            'polling_station', 'polling_station_name', 'total_voters', 'valid_votes',
            'invalid_votes', 'blank_votes', 'location_details', 'vote_entries',
            'total_valid_votes', 'voter_turnout', 'recorded_at', 'updated_at'
        ]
        read_only_fields = ['id', 'recorded_at', 'updated_at']
    
    def get_total_valid_votes(self, obj):
        """Obter total de votos válidos"""
        return obj.valid_votes
    
    def get_voter_turnout(self, obj):
        """Calcular percentagem de participação"""
        if obj.total_voters > 0:
            return round((obj.valid_votes / obj.total_voters) * 100, 2)
        return 0.0


class VoteTableCreateSerializer(serializers.ModelSerializer):
    """Serializer para criar uma nova mesa de voto"""
    
    class Meta:
        model = VoteTable
        fields = [
            'code', 'circunscricao', 'polling_station', 'total_voters',
            'invalid_votes', 'blank_votes', 'location_details'
        ]


# ============================================
# SERIALIZERS PARA SUBMISSÃO DE RESULTADOS
# ============================================

class VoteSubmissionSerializer(serializers.Serializer):
    """Serializer para submissão de resultados por agentes"""
    vote_table_code = serializers.CharField(max_length=20)
    circunscricao_code = serializers.CharField(max_length=20)
    results = VoteEntryCreateSerializer(many=True)
    invalid_votes = serializers.IntegerField(min_value=0, default=0)
    blank_votes = serializers.IntegerField(min_value=0, default=0)
    
    def validate(self, data):
        """Validar dados submetidos"""
        # Verificar se vote_table_code existe
        vote_table_code = data.get('vote_table_code')
        circunscricao_code = data.get('circunscricao_code')
        
        # Verificar se os votos não excedem o total de eleitores
        try:
            vote_table = VoteTable.objects.get(
                code=vote_table_code,
                circunscricao__code=circunscricao_code
            )
            total_voters = vote_table.total_voters
        except VoteTable.DoesNotExist:
            total_voters = None
        
        if total_voters:
            total_votes_submitted = sum(r.get('votes', 0) for r in data.get('results', []))
            total_votes_submitted += data.get('invalid_votes', 0)
            total_votes_submitted += data.get('blank_votes', 0)
            
            if total_votes_submitted > total_voters:
                raise serializers.ValidationError(
                    f"Total votes ({total_votes_submitted}) exceeds registered voters ({total_voters})"
                )
        
        return data


class VoteSubmissionResponseSerializer(serializers.Serializer):
    """Serializer para resposta de submissão"""
    message = serializers.CharField()
    vote_table_code = serializers.CharField()
    total_valid_votes = serializers.IntegerField()
    invalid_votes = serializers.IntegerField()
    blank_votes = serializers.IntegerField()


# ============================================
# SERIALIZERS PARA RESULTADOS AGREGADOS
# ============================================

class VoteResultSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source='party.name', read_only=True)
    party_abbreviation = serializers.CharField(source='party.abbreviation', read_only=True)
    party_color = serializers.CharField(source='party.color', read_only=True)
    circunscricao_code = serializers.CharField(source='circunscricao.code', read_only=True, allow_null=True)
    district_name = serializers.CharField(source='district.name', read_only=True, allow_null=True)
    percentage = serializers.SerializerMethodField()
    result_type_display = serializers.CharField(source='get_result_type_display', read_only=True)
    
    class Meta:
        model = VoteResult
        fields = [
            'id', 'result_type', 'result_type_display', 'party', 'party_name',
            'party_abbreviation', 'party_color', 'circunscricao', 'circunscricao_code',
            'district', 'district_name', 'vote_table', 'total_votes',
            'deputies_allocated', 'percentage', 'calculated_at', 'updated_at'
        ]
        read_only_fields = ['id', 'calculated_at', 'updated_at']
    
    def get_percentage(self, obj):
        """Calcular percentagem de votos para este partido"""
        # Buscar total de votos no mesmo nível
        total_votes = 0
        if obj.result_type == 'COUNTRY':
            total_votes = VoteResult.objects.filter(
                result_type='COUNTRY',
                country=obj.country
            ).aggregate(total=Sum('total_votes'))['total'] or 0
        elif obj.result_type == 'DISTRICT' and obj.district:
            total_votes = VoteResult.objects.filter(
                result_type='DISTRICT',
                district=obj.district
            ).aggregate(total=Sum('total_votes'))['total'] or 0
        elif obj.result_type == 'CIRCUNSCRICAO' and obj.circunscricao:
            total_votes = VoteResult.objects.filter(
                result_type='CIRCUNSCRICAO',
                circunscricao=obj.circunscricao
            ).aggregate(total=Sum('total_votes'))['total'] or 0
        elif obj.result_type == 'TABLE' and obj.vote_table:
            total_votes = VoteResult.objects.filter(
                result_type='TABLE',
                vote_table=obj.vote_table
            ).aggregate(total=Sum('total_votes'))['total'] or 0
        
        if total_votes > 0:
            return round((obj.total_votes / total_votes) * 100, 2)
        return 0.0


class PartyResultSerializer(serializers.Serializer):
    """Serializer para resultados por partido"""
    party = serializers.CharField()
    party_name = serializers.CharField()
    party_color = serializers.CharField()
    votes = serializers.IntegerField()
    percentage = serializers.FloatField()
    deputies = serializers.IntegerField()


class AggregatedResultSerializer(serializers.Serializer):
    """Serializer para resultados agregados por nível"""
    level = serializers.CharField()
    name = serializers.CharField()
    total_votes = serializers.IntegerField()
    total_deputies = serializers.IntegerField(required=False)
    results = PartyResultSerializer(many=True)


# ============================================
# SERIALIZERS PARA MÉTODO DE HONDT
# ============================================

class HondtCalculationSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source='party.name', read_only=True)
    party_abbreviation = serializers.CharField(source='party.abbreviation', read_only=True)
    party_color = serializers.CharField(source='party.color', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True)
    district_sigla = serializers.CharField(source='district.sigla', read_only=True)
    
    class Meta:
        model = HondtCalculation
        fields = [
            'id', 'district', 'district_name', 'district_sigla', 'party',
            'party_name', 'party_abbreviation', 'party_color', 'total_votes',
            'deputies_allocated', 'calculation_round', 'calculated_at'
        ]
        read_only_fields = ['id', 'calculated_at']


class HondtCalculationRequestSerializer(serializers.Serializer):
    """Serializer para requisição de cálculo de Hondt"""
    country_code = serializers.CharField(max_length=10, default='STP')
    total_seats = serializers.IntegerField(min_value=1, default=55)


class HondtResultSerializer(serializers.Serializer):
    """Serializer para resultado do método de Hondt"""
    district = serializers.CharField()
    district_sigla = serializers.CharField()
    total_deputies = serializers.IntegerField()
    parties = serializers.ListField(
        child=serializers.DictField()
    )


class HondtDetailSerializer(serializers.Serializer):
    """Serializer para detalhes do cálculo de Hondt"""
    total_deputies = serializers.IntegerField()
    calculations = HondtCalculationSerializer(many=True)
    by_district = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


# ============================================
# SERIALIZERS PARA ESTATÍSTICAS
# ============================================

class ElectionStatsSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source='country.name', read_only=True)
    country_code = serializers.CharField(source='country.code', read_only=True)
    voter_turnout_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = ElectionStats
        fields = [
            'id', 'country', 'country_name', 'country_code',
            'total_voters', 'total_valid_votes', 'total_invalid_votes',
            'total_blank_votes', 'voter_turnout', 'voter_turnout_percentage',
            'total_deputies', 'calculated_at', 'updated_at'
        ]
        read_only_fields = ['id', 'calculated_at', 'updated_at']
    
    def get_voter_turnout_percentage(self, obj):
        """Retornar percentagem de participação formatada"""
        return round(obj.voter_turnout, 2)


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer para estatísticas do dashboard"""
    election_stats = serializers.DictField()
    deputy_distribution = serializers.ListField(
        child=serializers.DictField()
    )
    district_votes = serializers.ListField(
        child=serializers.DictField()
    )
    top_parties = serializers.ListField(
        child=serializers.DictField()
    )
    recent_submissions = serializers.ListField(
        child=serializers.DictField()
    )


# ============================================
# SERIALIZERS PARA RELATÓRIOS
# ============================================

class ReportSummarySerializer(serializers.Serializer):
    """Serializer para resumo do relatório"""
    total_voters = serializers.IntegerField()
    total_valid_votes = serializers.IntegerField()
    voter_turnout = serializers.FloatField()
    total_deputies = serializers.IntegerField()


class PartyReportSerializer(serializers.Serializer):
    """Serializer para relatório de partidos"""
    party = serializers.CharField()
    abbreviation = serializers.CharField()
    votes = serializers.IntegerField()
    percentage = serializers.FloatField()
    deputies = serializers.IntegerField()


class DistrictReportSerializer(serializers.Serializer):
    """Serializer para relatório de distritos"""
    district = serializers.CharField()
    sigla = serializers.CharField()
    total_votes = serializers.IntegerField()
    deputies = serializers.IntegerField()


class FullReportSerializer(serializers.Serializer):
    """Serializer para relatório completo"""
    report_type = serializers.CharField()
    generated_at = serializers.DateTimeField()
    country = serializers.CharField()
    summary = ReportSummarySerializer()
    party_results = PartyReportSerializer(many=True)
    district_results = DistrictReportSerializer(many=True)


class SummaryReportSerializer(serializers.Serializer):
    """Serializer para relatório resumido"""
    report_type = serializers.CharField()
    generated_at = serializers.DateTimeField()
    country = serializers.CharField()
    total_voters = serializers.IntegerField()
    total_valid_votes = serializers.IntegerField()
    total_invalid_votes = serializers.IntegerField()
    total_blank_votes = serializers.IntegerField()
    voter_turnout = serializers.FloatField()
    total_deputies = serializers.IntegerField()
    top_parties = PartyReportSerializer(many=True)
    districts_summary = serializers.ListField(
        child=serializers.DictField()
    )


# ============================================
# SERIALIZERS AUXILIARES
# ============================================

class AgentSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    
    class Meta:
        model = Agent
        fields = ['id', 'user', 'email', 'username', 'first_name', 'last_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class OriginalDataImportSerializer(serializers.ModelSerializer):
    imported_by_email = serializers.CharField(source='imported_by', read_only=True)
    
    class Meta:
        model = OriginalDataImport
        fields = ['id', 'json_data', 'import_date', 'imported_by', 'imported_by_email', 'notes']
        read_only_fields = ['id', 'import_date']


class VoteTableSubmissionStatusSerializer(serializers.Serializer):
    """Serializer para status de submissão de mesas"""
    vote_table_code = serializers.CharField()
    submitted = serializers.BooleanField()
    submitted_at = serializers.DateTimeField(allow_null=True)
    submitted_by = serializers.CharField(allow_null=True)
    valid_votes = serializers.IntegerField()
    status = serializers.CharField()


# ============================================
# SERIALIZERS PARA VALIDAÇÃO
# ============================================

class VoteValidationSerializer(serializers.Serializer):
    """Serializer para validar dados de voto antes da submissão"""
    vote_table_code = serializers.CharField(max_length=20)
    circunscricao_code = serializers.CharField(max_length=20)
    total_voters = serializers.IntegerField()
    total_submitted_votes = serializers.IntegerField()
    difference = serializers.IntegerField()
    is_valid = serializers.BooleanField()
    warnings = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class BulkVoteSubmissionSerializer(serializers.Serializer):
    """Serializer para submissão em lote de várias mesas"""
    submissions = VoteSubmissionSerializer(many=True)
    
    def validate(self, data):
        """Validar todas as submissões em lote"""
        submissions = data.get('submissions', [])
        if not submissions:
            raise serializers.ValidationError("No submissions provided")
        
        # Verificar duplicados
        codes = [s.get('vote_table_code') for s in submissions]
        if len(codes) != len(set(codes)):
            raise serializers.ValidationError("Duplicate vote table codes found")
        
        return data


# ============================================
# SERIALIZERS PARA COMPARAÇÃO DE RESULTADOS
# ============================================

class ResultComparisonSerializer(serializers.Serializer):
    """Serializer para comparar resultados entre diferentes níveis"""
    level = serializers.CharField()
    name = serializers.CharField()
    total_votes = serializers.IntegerField()
    parties = serializers.DictField(
        child=serializers.DictField()
    )


class ElectionEvolutionSerializer(serializers.Serializer):
    """Serializer para evolução dos resultados ao longo do tempo"""
    timestamp = serializers.DateTimeField()
    total_votes = serializers.IntegerField()
    voter_turnout = serializers.FloatField()
    parties = serializers.DictField(
        child=serializers.DictField()
    )