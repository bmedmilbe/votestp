import logging

from django.db import transaction
from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
from .serializers import (
    AgentSerializer,
    CircunscricaoSerializer,
    CountrySerializer,
    DistrictSerializer,
    ElectionStatsSerializer,
    HondtCalculationSerializer,
    OriginalDataImportSerializer,
    PartySerializer,
    PollingStationSerializer,
    VoteEntrySerializer,
    VoteResultSerializer,
    VoteSubmissionResponseSerializer,
    VoteSubmissionSerializer,
    VoteTableCreateSerializer,
    VoteTableSerializer,
)

logger = logging.getLogger(__name__)


# ============================================
# VIEWSETS BÁSICOS (CRUD)
# ============================================

class CountryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar países
    """
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'code', 'total_deputies']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def districts(self, request, pk=None):
        """Listar todos os distritos de um país"""
        country = self.get_object()
        districts = District.objects.filter(country=country)
        serializer = DistrictSerializer(districts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Obter estatísticas de um país"""
        country = self.get_object()
        stats = ElectionStats.objects.filter(country=country).first()
        if stats:
            serializer = ElectionStatsSerializer(stats)
            return Response(serializer.data)
        return Response(
            {'message': 'No statistics available for this country'},
            status=status.HTTP_404_NOT_FOUND
        )


class DistrictViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar distritos
    """
    queryset = District.objects.all()
    serializer_class = DistrictSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'sigla']
    ordering_fields = ['name', 'sigla', 'total_deputies']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        country_code = self.request.query_params.get('country')
        if country_code:
            queryset = queryset.filter(country__code=country_code)
        return queryset

    @action(detail=True, methods=['get'])
    def circunscricoes(self, request, pk=None):
        """Listar todas as circunscrições de um distrito"""
        district = self.get_object()
        circunscricoes = Circunscricao.objects.filter(district=district)
        serializer = CircunscricaoSerializer(circunscricoes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Obter resultados agregados do distrito"""
        district = self.get_object()
        results = get_district_results(district)
        return Response(results)

    @action(detail=True, methods=['post'])
    def calculate_hondt(self, request, pk=None):
        """Calcular deputados para este distrito usando método de Hondt"""
        district = self.get_object()
        total_seats = request.data.get('total_seats', 55)
        
        try:
            with transaction.atomic():
                # Obter votos por partido no distrito
                party_votes = VoteEntry.objects.filter(
                    vote_table__circunscricao__district=district
                ).values('party').annotate(
                    total_votes=Sum('votes_count')
                ).order_by('-total_votes')
                
                # Aplicar método de Hondt
                hondt_results = apply_hondt_method(party_votes, total_seats)
                
                # Salvar resultados
                results = []
                for party_id, seats in hondt_results.items():
                    party = Party.objects.get(id=party_id)
                    calculation, created = HondtCalculation.objects.update_or_create(
                        district=district,
                        party=party,
                        # defaults={
                        #     'total_votes': party_votes.get(party_id=party_id, {}).get('total_votes', 0),
                        #     'deputies_allocated': seats
                        # }
                    )
                    results.append(calculation)
                
                # Atualizar distrito
                district.total_deputies = sum(hondt_results.values())
                district.save()
                
                serializer = HondtCalculationSerializer(results, many=True)
                return Response({
                    'message': 'Hondt method applied successfully',
                    'district': district.name,
                    'total_deputies': district.total_deputies,
                    'results': serializer.data
                })
                
        except Exception as e:
            logger.error(f"Error calculating Hondt: {e!s}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CircunscricaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar circunscrições
    """
    queryset = Circunscricao.objects.all()
    serializer_class = CircunscricaoSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['code', 'name']
    ordering_fields = ['code']
    ordering = ['code']

    def get_queryset(self):
        queryset = super().get_queryset()
        district_id = self.request.query_params.get('district')
        if district_id:
            queryset = queryset.filter(district_id=district_id)
        return queryset

    @action(detail=True, methods=['get'])
    def vote_tables(self, request, pk=None):
        """Listar todas as mesas de voto de uma circunscrição"""
        circunscricao = self.get_object()
        tables = VoteTable.objects.filter(circunscricao=circunscricao)
        serializer = VoteTableSerializer(tables, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Obter resultados agregados da circunscrição"""
        circunscricao = self.get_object()
        results = get_circunscricao_results(circunscricao)
        return Response(results)


class PollingStationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar estações de voto
    """
    queryset = PollingStation.objects.all()
    serializer_class = PollingStationSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        circunscricao_code = self.request.query_params.get('circunscricao')
        if circunscricao_code:
            queryset = queryset.filter(circunscricao__code=circunscricao_code)
        return queryset


class PartyViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar partidos políticos
    """
    queryset = Party.objects.all()
    serializer_class = PartySerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'abbreviation']
    ordering_fields = ['name', 'abbreviation', 'is_active']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Obter todos os resultados de um partido"""
        party = self.get_object()
        results = VoteResult.objects.filter(party=party).order_by('-total_votes')
        serializer = VoteResultSerializer(results, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def deputies(self, request, pk=None):
        """Obter todos os deputados de um partido"""
        party = self.get_object()
        hondt_results = HondtCalculation.objects.filter(party=party)
        serializer = HondtCalculationSerializer(hondt_results, many=True)
        return Response(serializer.data)


class VoteTableViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar mesas de voto
    """
    queryset = VoteTable.objects.all()
    serializer_class = VoteTableSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['code', 'location_details']
    ordering_fields = ['code', 'total_voters', 'valid_votes', 'recorded_at']
    ordering = ['code']

    def get_serializer_class(self):
        if self.action == 'create':
            return VoteTableCreateSerializer
        return VoteTableSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        circunscricao_code = self.request.query_params.get('circunscricao')
        if circunscricao_code:
            queryset = queryset.filter(circunscricao__code=circunscricao_code)
        
        district_id = self.request.query_params.get('district')
        if district_id:
            queryset = queryset.filter(circunscricao__district_id=district_id)
        
        is_complete = self.request.query_params.get('is_complete')
        if is_complete is not None:
            if is_complete.lower() == 'true':
                queryset = queryset.filter(valid_votes__gt=0)
            else:
                queryset = queryset.filter(valid_votes=0)
        
        return queryset

    @action(detail=True, methods=['post'])
    def submit_results(self, request, pk=None):
        """
        Submeter resultados para uma mesa específica
        """
        vote_table = self.get_object()
        
        # Verificar se o usuário é um agente
        try:
            agent = Agent.objects.get(user=request.user)
        except Agent.DoesNotExist:
            return Response(
                {'error': 'User is not an agent'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validar dados
        serializer = VoteSubmissionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                validated_data = serializer.validated_data
                results_data = validated_data.get('results', [])
                invalid_votes = validated_data.get('invalid_votes', 0)
                blank_votes = validated_data.get('blank_votes', 0)

                # Atualizar votos inválidos e brancos
                vote_table.invalid_votes = invalid_votes
                vote_table.blank_votes = blank_votes

                # Processar resultados por partido
                total_valid_votes = 0
                for result in results_data:
                    party_abbr = result.get('party_abbreviation')
                    votes = result.get('votes', 0)

                    if not party_abbr:
                        continue

                    # Buscar ou criar o partido
                    party, _ = Party.objects.get_or_create(
                        abbreviation=party_abbr,
                        defaults={'name': party_abbr, 'is_active': True}
                    )

                    # Criar ou atualizar entrada de votos
                    vote_entry, created = VoteEntry.objects.get_or_create(
                        vote_table=vote_table,
                        party=party,
                        defaults={'votes_count': votes}
                    )

                    if not created:
                        vote_entry.votes_count = votes
                        vote_entry.save()

                    total_valid_votes += votes

                # Atualizar votos válidos da mesa
                vote_table.valid_votes = total_valid_votes
                vote_table.save()

                # Atualizar resultados agregados
                update_aggregated_results(vote_table)

                response_data = {
                    'message': 'Vote results submitted successfully',
                    'vote_table_code': vote_table.code,
                    'total_valid_votes': total_valid_votes,
                    'invalid_votes': invalid_votes,
                    'blank_votes': blank_votes
                }
                
                response_serializer = VoteSubmissionResponseSerializer(data=response_data)
                response_serializer.is_valid()
                
                logger.info(f"Agent {request.user.email} submitted results for {vote_table.code}")
                
                return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error submitting vote results: {e!s}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def entries(self, request, pk=None):
        """Obter todas as entradas de voto de uma mesa"""
        vote_table = self.get_object()
        entries = VoteEntry.objects.filter(vote_table=vote_table).select_related('party')
        serializer = VoteEntrySerializer(entries, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Obter resultados detalhados de uma mesa"""
        vote_table = self.get_object()
        results = get_table_results(vote_table)
        return Response(results)


class VoteEntryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar entradas de voto
    """
    queryset = VoteEntry.objects.all()
    serializer_class = VoteEntrySerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['votes_count', 'recorded_at']
    ordering = ['-votes_count']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        vote_table_code = self.request.query_params.get('vote_table')
        if vote_table_code:
            queryset = queryset.filter(vote_table__code=vote_table_code)
        
        party_abbr = self.request.query_params.get('party')
        if party_abbr:
            queryset = queryset.filter(party__abbreviation=party_abbr)
        
        min_votes = self.request.query_params.get('min_votes')
        if min_votes:
            queryset = queryset.filter(votes_count__gte=int(min_votes))
        
        return queryset

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Criar múltiplas entradas de voto de uma vez
        """
        serializer = self.get_serializer(data=request.data, many=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                entries = serializer.save()
                return Response(
                    VoteEntrySerializer(entries, many=True).data,
                    status=status.HTTP_201_CREATED
                )
        except Exception as e:
            logger.error(f"Error in bulk create: {e!s}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================
# VIEWSETS PARA RESULTADOS E ESTATÍSTICAS
# ============================================

class VoteResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para visualizar resultados agregados
    """
    queryset = VoteResult.objects.all()
    serializer_class = VoteResultSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['total_votes', 'deputies_allocated', 'calculated_at']
    ordering = ['-total_votes']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        result_type = self.request.query_params.get('type')
        if result_type:
            queryset = queryset.filter(result_type=result_type)
        
        party_abbr = self.request.query_params.get('party')
        if party_abbr:
            queryset = queryset.filter(party__abbreviation=party_abbr)
        
        district_id = self.request.query_params.get('district')
        if district_id:
            queryset = queryset.filter(district_id=district_id)
        
        circunscricao_code = self.request.query_params.get('circunscricao')
        if circunscricao_code:
            queryset = queryset.filter(circunscricao__code=circunscricao_code)
        
        return queryset

    @action(detail=False, methods=['get'])
    def by_country(self, request):
        """Obter resultados agregados por país"""
        country_code = request.query_params.get('country', 'STP')
        country = get_object_or_404(Country, code=country_code)
        results = get_country_results(country)
        return Response(results)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Obter resumo de todos os resultados"""
        country_code = request.query_params.get('country', 'STP')
        country = get_object_or_404(Country, code=country_code)
        
        # Estatísticas gerais
        stats = ElectionStats.objects.filter(country=country).first()
        
        # Resultados por partido
        party_results = VoteResult.objects.filter(
            result_type='COUNTRY',
            country=country
        ).select_related('party').order_by('-total_votes')
        
        # Resultados por distrito
        district_results = District.objects.filter(country=country).annotate(
            total_votes=Sum('circunscricoes__vote_tables__vote_entries__votes_count'),
            total_deputies=Sum('hondt_calculations__deputies_allocated')
        )
        
        data = {
            'country': country.name,
            'total_voters': stats.total_voters if stats else 0,
            'total_valid_votes': stats.total_valid_votes if stats else 0,
            'voter_turnout': stats.voter_turnout if stats else 0,
            'total_deputies': stats.total_deputies if stats else 55,
            'parties': [
                {
                    'party': r.party.abbreviation,
                    'party_name': r.party.name,
                    'party_color': r.party.color,
                    'votes': r.total_votes,
                    'percentage': round((r.total_votes / (stats.total_valid_votes if stats else 1) * 100), 2),
                    'deputies': r.deputies_allocated
                }
                for r in party_results
            ],
            'districts': [
                {
                    'name': d.name,
                    'sigla': d.sigla,
                    'votes': d.total_votes or 0,
                    'deputies': d.total_deputies or 0
                }
                for d in district_results
            ]
        }
        
        return Response(data)


class HondtCalculationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para visualizar cálculos do método de Hondt
    """
    queryset = HondtCalculation.objects.all()
    serializer_class = HondtCalculationSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['deputies_allocated', 'total_votes', 'calculated_at']
    ordering = ['-deputies_allocated']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        district_id = self.request.query_params.get('district')
        if district_id:
            queryset = queryset.filter(district_id=district_id)
        
        party_abbr = self.request.query_params.get('party')
        if party_abbr:
            queryset = queryset.filter(party__abbreviation=party_abbr)
        
        return queryset

    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """
        Calcular todos os deputados usando método de Hondt para um país
        """
        country_code = request.data.get('country_code', 'STP')
        total_seats = request.data.get('total_seats', 55)
        
        country = get_object_or_404(Country, code=country_code)
        
        try:
            with transaction.atomic():
                # Para cada distrito, calcular a distribuição de deputados
                districts = District.objects.filter(country=country)
                results = []
                
                for district in districts:
                    # Obter votos por partido no distrito
                    party_votes = VoteEntry.objects.filter(
                        vote_table__circunscricao__district=district
                    ).values('party').annotate(
                        total_votes=Sum('votes_count')
                    ).order_by('-total_votes')
                    
                    # Calcular quantos deputados o distrito recebe
                    district_seats = calculate_district_seats(district, total_seats)
                    district.total_deputies = district_seats
                    district.save()
                    
                    # Aplicar método de Hondt
                    hondt_results = apply_hondt_method(party_votes, district_seats)
                    
                    # Salvar resultados
                    district_results = []
                    for party_id, seats in hondt_results.items():
                        party = Party.objects.get(id=party_id)
                        calculation, _ = HondtCalculation.objects.update_or_create(
                            district=district,
                            party=party,
                            # defaults={
                            #     'total_votes': party_votes.get(party_id=party_id, {}).get('total_votes', 0),
                            #     'deputies_allocated': seats
                            # }
                        )
                        district_results.append(calculation)
                    
                    results.append({
                        'district': district.name,
                        'total_seats': district_seats,
                        'results': HondtCalculationSerializer(district_results, many=True).data
                    })
                
                # Atualizar estatísticas
                update_election_stats(country)
                
                return Response({
                    'message': 'Hondt method applied successfully',
                    'country': country.name,
                    'total_seats': total_seats,
                    'districts_processed': len(results),
                    'results': results
                })
                
        except Exception as e:
            logger.error(f"Error calculating Hondt: {e!s}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Obter resumo da distribuição de deputados"""
        country_code = request.query_params.get('country', 'STP')
        country = get_object_or_404(Country, code=country_code)
        
        # Distribuição de deputados por partido
        deputy_distribution = HondtCalculation.objects.filter(
            district__country=country
        ).values('party__abbreviation', 'party__name', 'party__color').annotate(
            total_deputies=Sum('deputies_allocated'),
            total_votes=Sum('total_votes')
        ).order_by('-total_deputies')
        
        # Distribuição por distrito
        district_distribution = HondtCalculation.objects.filter(
            district__country=country
        ).values('district__name', 'district__sigla').annotate(
            total_deputies=Sum('deputies_allocated'),
            total_votes=Sum('total_votes')
        ).order_by('-total_deputies')
        
        # Total de deputados
        total_deputies = sum(d['total_deputies'] for d in deputy_distribution)
        
        return Response({
            'country': country.name,
            'total_deputies': total_deputies,
            'by_party': list(deputy_distribution),
            'by_district': list(district_distribution)
        })


# ============================================
# VIEWSETS PARA DASHBOARD E RELATÓRIOS
# ============================================

class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet para dados do dashboard
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obter estatísticas completas para o dashboard"""
        country_code = request.query_params.get('country', 'STP')
        country = get_object_or_404(Country, code=country_code)
        
        try:
            # Estatísticas gerais
            stats = ElectionStats.objects.filter(country=country).first()
            
            # Distribuição de deputados
            deputy_distribution = HondtCalculation.objects.filter(
                district__country=country
            ).values('party__abbreviation', 'party__name', 'party__color').annotate(
                total_deputies=Sum('deputies_allocated')
            ).order_by('-total_deputies')
            
            # Votação por distrito
            district_votes = VoteResult.objects.filter(
                result_type='DISTRICT',
                district__country=country
            ).values('district__name').annotate(
                total_votes=Sum('total_votes')
            ).order_by('-total_votes')
            
            # Top partidos por votos
            top_parties = VoteResult.objects.filter(
                result_type='COUNTRY',
                country=country
            ).select_related('party').order_by('-total_votes')[:10]
            
            # Últimas submissões
            recent_submissions = VoteTable.objects.filter(
                circunscricao__district__country=country
            ).order_by('-updated_at')[:10]
            
            # Estatísticas de mesas
            total_tables = VoteTable.objects.filter(
                circunscricao__district__country=country
            ).count()
            
            completed_tables = VoteTable.objects.filter(
                circunscricao__district__country=country,
                valid_votes__gt=0
            ).count()
            
            data = {
                'election_stats': {
                    'total_voters': stats.total_voters if stats else 0,
                    'total_valid_votes': stats.total_valid_votes if stats else 0,
                    'total_invalid_votes': stats.total_invalid_votes if stats else 0,
                    'total_blank_votes': stats.total_blank_votes if stats else 0,
                    'voter_turnout': stats.voter_turnout if stats else 0,
                    'total_deputies': stats.total_deputies if stats else 55
                },
                'progress': {
                    'total_tables': total_tables,
                    'completed_tables': completed_tables,
                    'completion_percentage': round((completed_tables / total_tables * 100), 2) if total_tables > 0 else 0
                },
                'deputy_distribution': list(deputy_distribution),
                'district_votes': list(district_votes),
                'top_parties': [
                    {
                        'party': r.party.abbreviation,
                        'party_name': r.party.name,
                        'party_color': r.party.color,
                        'votes': r.total_votes,
                        'percentage': round((r.total_votes / (stats.total_valid_votes if stats else 1) * 100), 2)
                    }
                    for r in top_parties
                ],
                'recent_submissions': [
                    {
                        'code': t.code,
                        'circunscricao': t.circunscricao.code,
                        'valid_votes': t.valid_votes,
                        'updated_at': t.updated_at
                    }
                    for t in recent_submissions
                ]
            }
            
            return Response(data)
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e!s}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Obter visão geral rápida para o dashboard"""
        country_code = request.query_params.get('country', 'STP')
        country = get_object_or_404(Country, code=country_code)
        
        # Contagens rápidas
        total_districts = District.objects.filter(country=country).count()
        total_circunscricoes = Circunscricao.objects.filter(district__country=country).count()
        total_tables = VoteTable.objects.filter(circunscricao__district__country=country).count()
        
        # Votos totais
        total_votes = VoteEntry.objects.filter(
            vote_table__circunscricao__district__country=country
        ).aggregate(total=Sum('votes_count'))['total'] or 0
        
        # Deputados totais
        total_deputies = HondtCalculation.objects.filter(
            district__country=country
        ).aggregate(total=Sum('deputies_allocated'))['total'] or 0
        
        return Response({
            'country': country.name,
            'statistics': {
                'districts': total_districts,
                'circunscricoes': total_circunscricoes,
                'vote_tables': total_tables,
                'total_votes': total_votes,
                'total_deputies': total_deputies
            }
        })


class ReportViewSet(viewsets.ViewSet):
    """
    ViewSet para gerar relatórios
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def full(self, request):
        """Gerar relatório completo"""
        country_code = request.query_params.get('country', 'STP')
        country = get_object_or_404(Country, code=country_code)
        
        try:
            report = generate_full_report(country)
            return Response(report)
        except Exception as e:
            logger.error(f"Error generating full report: {e!s}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Gerar relatório resumido"""
        country_code = request.query_params.get('country', 'STP')
        country = get_object_or_404(Country, code=country_code)
        
        try:
            stats = ElectionStats.objects.filter(country=country).first()
            
            # Top 5 partidos
            top_parties = VoteResult.objects.filter(
                result_type='COUNTRY',
                country=country
            ).select_related('party').order_by('-total_votes')[:5]
            
            # Resumo por distrito
            district_summary = District.objects.filter(country=country).annotate(
                total_votes=Sum('circunscricoes__vote_tables__vote_entries__votes_count'),
                total_deputies=Sum('hondt_calculations__deputies_allocated')
            ).order_by('-total_votes')
            
            report = {
                'report_type': 'summary',
                'generated_at': timezone.now().isoformat(),
                'country': country.name,
                'total_voters': stats.total_voters if stats else 0,
                'total_valid_votes': stats.total_valid_votes if stats else 0,
                'total_invalid_votes': stats.total_invalid_votes if stats else 0,
                'total_blank_votes': stats.total_blank_votes if stats else 0,
                'voter_turnout': stats.voter_turnout if stats else 0,
                'total_deputies': stats.total_deputies if stats else 55,
                'top_parties': [
                    {
                        'party': r.party.abbreviation,
                        'party_name': r.party.name,
                        'votes': r.total_votes,
                        'percentage': round((r.total_votes / (stats.total_valid_votes if stats else 1) * 100), 2),
                        'deputies': r.deputies_allocated
                    }
                    for r in top_parties
                ],
                'districts_summary': [
                    {
                        'name': d.name,
                        'sigla': d.sigla,
                        'votes': d.total_votes or 0,
                        'deputies': d.total_deputies or 0
                    }
                    for d in district_summary
                ]
            }
            
            return Response(report)
            
        except Exception as e:
            logger.error(f"Error generating summary report: {e!s}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def parties(self, request):
        """Gerar relatório de partidos"""
        country_code = request.query_params.get('country', 'STP')
        country = get_object_or_404(Country, code=country_code)
        
        try:
            # Todos os partidos com seus resultados
            party_results = VoteResult.objects.filter(
                result_type='COUNTRY',
                country=country
            ).select_related('party').order_by('-total_votes')
            
            total_votes = sum(r.total_votes for r in party_results)
            
            report = {
                'report_type': 'parties',
                'generated_at': timezone.now().isoformat(),
                'country': country.name,
                'total_votes': total_votes,
                'parties': [
                    {
                        'abbreviation': r.party.abbreviation,
                        'name': r.party.name,
                        'color': r.party.color,
                        'votes': r.total_votes,
                        'percentage': round((r.total_votes / total_votes * 100), 2) if total_votes > 0 else 0,
                        'deputies': r.deputies_allocated,
                        'status': 'active' if r.party.is_active else 'inactive'
                    }
                    for r in party_results
                ]
            }
            
            return Response(report)
            
        except Exception as e:
            logger.error(f"Error generating parties report: {e!s}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def districts(self, request):
        """Gerar relatório de distritos"""
        country_code = request.query_params.get('country', 'STP')
        country = get_object_or_404(Country, code=country_code)
        
        try:
            districts = District.objects.filter(country=country).annotate(
                total_votes=Sum('circunscricoes__vote_tables__vote_entries__votes_count'),
                total_deputies=Sum('hondt_calculations__deputies_allocated'),
                voter_turnout=Avg('circunscricoes__vote_tables__valid_votes')  # Simplificado
            )
            
            report = {
                'report_type': 'districts',
                'generated_at': timezone.now().isoformat(),
                'country': country.name,
                'districts': [
                    {
                        'name': d.name,
                        'sigla': d.sigla,
                        'total_votes': d.total_votes or 0,
                        'deputies': d.total_deputies or 0,
                        'circunscricoes': Circunscricao.objects.filter(district=d).count(),
                        'tables': VoteTable.objects.filter(circunscricao__district=d).count()
                    }
                    for d in districts
                ]
            }
            
            return Response(report)
            
        except Exception as e:
            logger.error(f"Error generating districts report: {e!s}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================
# VIEWSETS PARA AGENTES E IMPORTAÇÕES
# ============================================

class AgentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar agentes
    """
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['user__email', 'user__username']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        """Obter todas as submissões de um agente"""
        agent = self.get_object()
        submissions = VoteTable.objects.filter(
            recorded_by=agent  # Você precisará adicionar este campo ao modelo
        ).order_by('-recorded_at')
        serializer = VoteTableSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_submissions(self, request):
        """Obter submissões do agente atual"""
        try:
            agent = Agent.objects.get(user=request.user)
            submissions = VoteTable.objects.filter(
                recorded_by=agent
            ).order_by('-recorded_at')
            serializer = VoteTableSerializer(submissions, many=True)
            return Response(serializer.data)
        except Agent.DoesNotExist:
            return Response(
                {'error': 'User is not an agent'},
                status=status.HTTP_403_FORBIDDEN
            )


class OriginalDataImportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para visualizar importações de dados
    """
    queryset = OriginalDataImport.objects.all()
    serializer_class = OriginalDataImportSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['import_date']
    ordering = ['-import_date']

    @action(detail=True, methods=['get'])
    def data(self, request, pk=None):
        """Obter os dados JSON importados"""
        import_obj = self.get_object()
        return Response(import_obj.json_data)


# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def update_aggregated_results(vote_table):
    """Atualizar resultados agregados após submissão"""
    circunscricao = vote_table.circunscricao
    district = circunscricao.district
    
    # Atualizar resultados por circunscrição
    update_circunscricao_results(circunscricao)
    
    # Atualizar resultados por distrito
    update_district_results(district)
    
    # Atualizar resultados do país
    update_country_results(district.country)


def update_circunscricao_results(circunscricao):
    """Atualizar resultados agregados por circunscrição"""
    party_votes = VoteEntry.objects.filter(
        vote_table__circunscricao=circunscricao
    ).values('party').annotate(
        total_votes=Sum('votes_count')
    )
    
    for pv in party_votes:
        party = Party.objects.get(id=pv['party'])
        VoteResult.objects.update_or_create(
            result_type='CIRCUNSCRICAO',
            party=party,
            circunscricao=circunscricao,
            defaults={
                'total_votes': pv['total_votes']
            }
        )


def update_district_results(district):
    """Atualizar resultados agregados por distrito"""
    party_votes = VoteEntry.objects.filter(
        vote_table__circunscricao__district=district
    ).values('party').annotate(
        total_votes=Sum('votes_count')
    )
    
    for pv in party_votes:
        party = Party.objects.get(id=pv['party'])
        VoteResult.objects.update_or_create(
            result_type='DISTRICT',
            party=party,
            district=district,
            defaults={
                'total_votes': pv['total_votes']
            }
        )


def update_country_results(country):
    """Atualizar resultados agregados por país"""
    party_votes = VoteEntry.objects.filter(
        vote_table__circunscricao__district__country=country
    ).values('party').annotate(
        total_votes=Sum('votes_count')
    )
    
    for pv in party_votes:
        party = Party.objects.get(id=pv['party'])
        VoteResult.objects.update_or_create(
            result_type='COUNTRY',
            party=party,
            defaults={
                'total_votes': pv['total_votes']
            }
        )


def update_election_stats(country):
    """Atualizar estatísticas gerais da eleição"""
    total_voters = VoteTable.objects.filter(
        circunscricao__district__country=country
    ).aggregate(total=Sum('total_voters'))['total'] or 0
    
    total_valid = VoteEntry.objects.filter(
        vote_table__circunscricao__district__country=country
    ).aggregate(total=Sum('votes_count'))['total'] or 0
    
    total_invalid = VoteTable.objects.filter(
        circunscricao__district__country=country
    ).aggregate(total=Sum('invalid_votes'))['total'] or 0
    
    total_blank = VoteTable.objects.filter(
        circunscricao__district__country=country
    ).aggregate(total=Sum('blank_votes'))['total'] or 0
    
    voter_turnout = (total_valid / total_voters * 100) if total_voters > 0 else 0
    
    stats, _ = ElectionStats.objects.update_or_create(
        country=country,
        defaults={
            'total_voters': total_voters,
            'total_valid_votes': total_valid,
            'total_invalid_votes': total_invalid,
            'total_blank_votes': total_blank,
            'voter_turnout': voter_turnout,
            'total_deputies': 55
        }
    )


def calculate_district_seats(district, total_seats):
    """Calcular quantos deputados um distrito recebe"""
    total_voters = VoteTable.objects.filter(
        circunscricao__district__country=district.country
    ).aggregate(total=Sum('total_voters'))['total'] or 1
    
    district_voters = VoteTable.objects.filter(
        circunscricao__district=district
    ).aggregate(total=Sum('total_voters'))['total'] or 0
    
    seats = int((district_voters / total_voters) * total_seats)
    return max(1, seats)


def apply_hondt_method(party_votes, total_seats):
    """Aplicar método de Hondt para distribuir deputados"""
    parties = []
    for pv in party_votes:
        parties.append({
            'party_id': pv['party'],
            'votes': pv['total_votes']
        })
    
    if not parties:
        return {}
    
    results = {p['party_id']: 0 for p in parties}
    
    for _ in range(total_seats):
        max_quotient = 0
        selected_party = None
        
        for party in parties:
            party_id = party['party_id']
            votes = party['votes']
            allocated = results[party_id]
            quotient = votes / (allocated + 1)
            
            if quotient > max_quotient:
                max_quotient = quotient
                selected_party = party_id
        
        if selected_party is not None:
            results[selected_party] += 1
    
    return results


def get_country_results(country):
    """Obter resultados agregados do país"""
    vote_results = VoteResult.objects.filter(
        result_type='COUNTRY',
        party__is_active=True
    ).select_related('party').order_by('-total_votes')
    
    total_votes = sum(r.total_votes for r in vote_results)
    
    return {
        'level': 'country',
        'country': country.name,
        'total_votes': total_votes,
        'results': [
            {
                'party': r.party.abbreviation,
                'party_name': r.party.name,
                'party_color': r.party.color,
                'votes': r.total_votes,
                'percentage': round((r.total_votes / total_votes * 100), 2) if total_votes > 0 else 0,
                'deputies': r.deputies_allocated
            }
            for r in vote_results
        ]
    }


def get_district_results(district):
    """Obter resultados agregados do distrito"""
    vote_results = VoteResult.objects.filter(
        result_type='DISTRICT',
        district=district,
        party__is_active=True
    ).select_related('party').order_by('-total_votes')
    
    total_votes = sum(r.total_votes for r in vote_results)
    
    return {
        'level': 'district',
        'district': district.name,
        'country': district.country.name,
        'total_votes': total_votes,
        'total_deputies': district.total_deputies,
        'results': [
            {
                'party': r.party.abbreviation,
                'party_name': r.party.name,
                'party_color': r.party.color,
                'votes': r.total_votes,
                'percentage': round((r.total_votes / total_votes * 100), 2) if total_votes > 0 else 0,
                'deputies': r.deputies_allocated
            }
            for r in vote_results
        ]
    }


def get_circunscricao_results(circunscricao):
    """Obter resultados agregados da circunscrição"""
    vote_results = VoteResult.objects.filter(
        result_type='CIRCUNSCRICAO',
        circunscricao=circunscricao,
        party__is_active=True
    ).select_related('party').order_by('-total_votes')
    
    total_votes = sum(r.total_votes for r in vote_results)
    
    return {
        'level': 'circunscricao',
        'circunscricao': circunscricao.code,
        'district': circunscricao.district.name,
        'total_votes': total_votes,
        'results': [
            {
                'party': r.party.abbreviation,
                'party_name': r.party.name,
                'party_color': r.party.color,
                'votes': r.total_votes,
                'percentage': round((r.total_votes / total_votes * 100), 2) if total_votes > 0 else 0
            }
            for r in vote_results
        ]
    }


def get_table_results(vote_table):
    """Obter resultados de uma mesa específica"""
    vote_entries = VoteEntry.objects.filter(
        vote_table=vote_table,
        party__is_active=True
    ).select_related('party').order_by('-votes_count')
    
    return {
        'level': 'table',
        'vote_table': vote_table.code,
        'circunscricao': vote_table.circunscricao.code,
        'total_voters': vote_table.total_voters,
        'valid_votes': vote_table.valid_votes,
        'invalid_votes': vote_table.invalid_votes,
        'blank_votes': vote_table.blank_votes,
        'results': [
            {
                'party': entry.party.abbreviation,
                'party_name': entry.party.name,
                'party_color': entry.party.color,
                'votes': entry.votes_count,
                'percentage': round((entry.votes_count / vote_table.valid_votes * 100), 2) 
                    if vote_table.valid_votes > 0 else 0
            }
            for entry in vote_entries
        ]
    }


def generate_full_report(country):
    """Gerar relatório completo"""
    stats = ElectionStats.objects.filter(country=country).first()
    
    party_results = VoteResult.objects.filter(
        result_type='COUNTRY',
        country=country
    ).select_related('party').order_by('-total_votes')
    
    district_results = District.objects.filter(country=country).annotate(
        total_votes=Sum('circunscricoes__vote_tables__vote_entries__votes_count'),
        total_deputies=Sum('hondt_calculations__deputies_allocated')
    )
    
    return {
        'report_type': 'full',
        'generated_at': timezone.now().isoformat(),
        'country': country.name,
        'summary': {
            'total_voters': stats.total_voters if stats else 0,
            'total_valid_votes': stats.total_valid_votes if stats else 0,
            'voter_turnout': stats.voter_turnout if stats else 0,
            'total_deputies': stats.total_deputies if stats else 55
        },
        'party_results': [
            {
                'party': r.party.name,
                'abbreviation': r.party.abbreviation,
                'votes': r.total_votes,
                'percentage': round((r.total_votes / (stats.total_valid_votes if stats else 1) * 100), 2),
                'deputies': r.deputies_allocated
            }
            for r in party_results
        ],
        'district_results': [
            {
                'district': d.name,
                'sigla': d.sigla,
                'total_votes': d.total_votes or 0,
                'deputies': d.total_deputies or 0
            }
            for d in district_results
        ]
    }