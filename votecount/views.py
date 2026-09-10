import logging

from django.db.models import Sum
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import (
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
from .serializers import (
    CircunscricaoSerializer,
    CountrySerializer,
    DistrictSerializer,
    PartySerializer,
    PollingStationSerializer,
    ResultPerPartySerializer,
    VoteEntryCreateSerializer,
    VoteEntrySerializer,
    VoteTableCreateSerializer,
    VoteTableSerializer,
)

logger = logging.getLogger(__name__)
class LargeResultsSetPagination(PageNumberPagination):
    page_size = 1000
   
class ReadOnlyViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Base viewset for read-only access"""
    permission_classes = [IsAuthenticatedOrReadOnly]


class AgentWriteViewSet(viewsets.ModelViewSet):
    """Base viewset for agent write access (only VoteTable and VoteEntry)"""
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        """Agent can create data"""
        serializer.save()
    
    def perform_update(self, serializer):
        """Agent can update data"""
        serializer.save()
    
    def perform_destroy(self, instance):
        """Agent can delete data"""
        instance.delete()


# ============================================
# READ-ONLY VIEWSETS WITH NESTED SUPPORT
# ============================================

class CountryViewSet(ReadOnlyViewSet):
    """
    Country viewset - read only
    Nested routes:
    - /countries/{pk}/districts/
    - /countries/{pk}/results/
    - /countries/{pk}/deputies/
    """
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    lookup_field = 'pk'


class DistrictViewSet(ReadOnlyViewSet):
    """
    District viewset - read only
    Nested routes:
    - /countries/{country_pk}/districts/{pk}/
    - /districts/{pk}/circunscricoes/
    - /districts/{pk}/votetables/
    - /districts/{pk}/results/
    - /districts/{pk}/deputies/
    """
    queryset = District.objects.all()
    serializer_class = DistrictSerializer
    lookup_field = 'pk'
    ordering_fields = ['name', 'sigla', 'total_deputies']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by country if nested
        country_pk = self.kwargs.get('country_pk')
        if country_pk:
            queryset = queryset.filter(country_id=country_pk)
        return queryset


class CircunscricaoViewSet(ReadOnlyViewSet):
    """
    Circunscricao viewset - read only
    Nested routes:
    - /districts/{district_pk}/circunscricoes/{pk}/
    - /circunscricoes/{pk}/votetables/
    - /circunscricoes/{pk}/results/
    """
    queryset = Circunscricao.objects.all()
    serializer_class = CircunscricaoSerializer
    lookup_field = 'pk'
    search_fields = ['code', 'name']
    ordering_fields = ['code']
    ordering = ['code']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by district if nested
        district_pk = self.kwargs.get('district_pk')
        if district_pk:
            queryset = queryset.filter(district_id=district_pk)
        return queryset


class PollingStationViewSet(ReadOnlyViewSet):
    """
    PollingStation viewset - read only
    Nested routes:
    - /circunscricoes/{circunscricao_pk}/polling-stations/
    """
    queryset = PollingStation.objects.all()
    serializer_class = PollingStationSerializer
    lookup_field = 'pk'
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by circunscricao if nested
        circunscricao_pk = self.kwargs.get('circunscricao_pk')
        if circunscricao_pk:
            queryset = queryset.filter(circunscricao_id=circunscricao_pk)
        return queryset


class PartyViewSet(ReadOnlyViewSet):
    """
    Party viewset - read only
    """
    queryset = Party.objects.all()
    serializer_class = PartySerializer
    lookup_field = 'pk'
    search_fields = ['name', 'abbreviation']
    ordering_fields = ['name', 'abbreviation', 'is_active']
    ordering = ['name']


# ============================================
# NESTED RESULT VIEWSETS (READ-ONLY)
# ============================================

class ResultPerCountryViewSet(ReadOnlyViewSet):
    """
    Results per country - read only
    Nested route: /countries/{country_pk}/results/
    """
    serializer_class = ResultPerPartySerializer
    lookup_field = 'pk'
    
    def get_queryset(self):
        country_pk = self.kwargs.get('country_pk')
        if country_pk:
            return ResultPerCountryPerParty.objects.filter(
                country_id=country_pk
            ).select_related('party')
        return ResultPerCountryPerParty.objects.none()


class ResultPerDistrictViewSet(ReadOnlyViewSet):
    """
    Results per district - read only
    Nested route: /districts/{district_pk}/results/
    """
    serializer_class = ResultPerPartySerializer
    lookup_field = 'pk'
    
    def get_queryset(self):
        district_pk = self.kwargs.get('district_pk')
        if district_pk:
            return ResultPerDistrictPerParty.objects.filter(
                district_id=district_pk
            ).select_related('party')
        return ResultPerDistrictPerParty.objects.none()


class ResultPerCircunscricaoViewSet(ReadOnlyViewSet):
    """
    Results per circunscricao - read only
    Nested route: /circunscricoes/{circunscricao_pk}/results/
    """
    serializer_class = ResultPerPartySerializer
    lookup_field = 'pk'
    
    def get_queryset(self):
        circunscricao_pk = self.kwargs.get('circunscricao_pk')
        if circunscricao_pk:
            return ResultPerCircunscricaoPerParty.objects.filter(
                circunscricao_id=circunscricao_pk
            ).select_related('party')
        return ResultPerCircunscricaoPerParty.objects.none()




# ============================================
# NESTED VOTE TABLE VIEWSETS
# ============================================

class VoteTableViewSet(AgentWriteViewSet):
    """
    VoteTable viewset - agents can write
    Nested routes:
    - /circunscricoes/{circunscricao_pk}/votetables/
    - /districts/{district_pk}/votetables/
    - /votetables/{pk}/voteentries/
    - /votetables/{pk}/summary/
    """
    queryset = VoteTable.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    search_fields = ['code', 'location_details']
    ordering_fields = ['code', 'total_voters', 'valid_votes', 'recorded_at']
    ordering = ['code']
    pagination_class = LargeResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'update':
            return VoteTableCreateSerializer
        return VoteTableSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by circunscricao if nested
        circunscricao_pk = self.kwargs.get('circunscricao_pk')
        if circunscricao_pk:
            queryset = queryset.filter(circunscricao_id=circunscricao_pk)
        
        # Filter by district if nested (through circunscricao)
        district_pk = self.kwargs.get('district_pk')
        if district_pk:
            queryset = queryset.filter(circunscricao__district_id=district_pk)
        
        return queryset
    
    @action(detail=True, methods=['get'], url_path='summary')
    def get_summary(self, request, pk=None):
        """Get summary of votes for a specific vote table"""
        vote_table = self.get_object()
        total_votes = vote_table.vote_entries.aggregate(total=Sum('votes_count'))['total'] or 0
        
        data = {
            'code': vote_table.code,
            'total_voters': vote_table.total_voters,
            'valid_votes': vote_table.valid_votes,
            'invalid_votes': vote_table.invalid_votes,
            'blank_votes': vote_table.blank_votes,
            'total_votes_cast': total_votes,
            'turnout_percentage': (total_votes / vote_table.total_voters * 100) if vote_table.total_voters > 0 else 0,
            'circunscricao': vote_table.circunscricao.code,
            'polling_station': vote_table.polling_station.name
        }
        return Response(data)


class VoteEntryViewSet(AgentWriteViewSet):
    """
    VoteEntry viewset - agents can write
    Nested routes:
    - /votetables/{vote_table_pk}/voteentries/
    """

    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'pk'
    ordering_fields = ['votes_count', 'recorded_at']
    ordering = ['-votes_count']

    def get_queryset(self):
        return VoteEntry.objects.filter(vote_table_id=self.kwargs['vote_table_pk'])

    def get_serializer_class(self):
        if self.request.method == "POST":
            return VoteEntryCreateSerializer
        return VoteEntrySerializer
    def get_serializer_context(self):
        return {
            "user_id": self.request.user, 
            "vote_table_pk": self.kwargs['vote_table_pk']
        }
    
    
# ============================================
# SIMPLIFIED NESTED LIST VIEWSETS
# ============================================

class CountryDistrictsViewSet(ReadOnlyViewSet):
    """
    List districts for a specific country
    Nested route: /countries/{country_pk}/districts/
    """
    serializer_class = DistrictSerializer
    
    def get_queryset(self):
        country_pk = self.kwargs.get('country_pk')
        if country_pk:
            return District.objects.filter(country_id=country_pk)
        return District.objects.none()


class DistrictCircunscricoesViewSet(ReadOnlyViewSet):
    """
    List circunscricoes for a specific district
    Nested route: /districts/{district_pk}/circunscricoes/
    """
    serializer_class = CircunscricaoSerializer
    
    def get_queryset(self):
        district_pk = self.kwargs.get('district_pk')
        if district_pk:
            return Circunscricao.objects.filter(district_id=district_pk)
        return Circunscricao.objects.none()


class CircunscricaoPollingStationsViewSet(ReadOnlyViewSet):
    """
    List polling stations for a specific circunscricao
    Nested route: /circunscricoes/{circunscricao_pk}/polling-stations/
    """
    serializer_class = PollingStationSerializer
    
    def get_queryset(self):
        circunscricao_pk = self.kwargs.get('circunscricao_pk')
        if circunscricao_pk:
            return PollingStation.objects.filter(circunscricao_id=circunscricao_pk)
        return PollingStation.objects.none()