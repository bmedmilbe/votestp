from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html

from .models import (
    Agent,
    Circunscricao,
    Country,
    DeputiesPerCountryPerParty,
    DeputiesPerDistrictPerParty,
    District,
    Party,
    PollingStation,
    ResultPerCircunscricaoPerParty,
    ResultPerCountryPerParty,
    ResultPerDistrictPerParty,
    VoteEntry,
    VoteTable,
)

# ============================================
# INLINE ADMIN CLASSES
# ============================================

class VoteEntryInline(admin.TabularInline):
    """Inline for VoteEntry within VoteTable"""
    model = VoteEntry
    extra = 1
    fields = ['party', 'votes_count', 'recorded_at', 'updated_at']
    readonly_fields = ['recorded_at', 'updated_at']
    autocomplete_fields = ['party']
    ordering = ['-votes_count']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('party')


class VoteTableInline(admin.TabularInline):
    """Inline for VoteTable within Circunscricao"""
    model = VoteTable
    extra = 0
    fields = ['code', 'polling_station', 'total_voters', 'valid_votes', 
              'invalid_votes', 'blank_votes', 'recorded_at']
    readonly_fields = ['recorded_at']
    autocomplete_fields = ['polling_station']
    ordering = ['code']


class PollingStationInline(admin.TabularInline):
    """Inline for PollingStation within Circunscricao"""
    model = PollingStation
    extra = 1
    fields = ['name']
    ordering = ['name']


class CircunscricaoInline(admin.TabularInline):
    """Inline for Circunscricao within District"""
    model = Circunscricao
    extra = 0
    fields = ['code', 'name']
    ordering = ['code']


class DistrictInline(admin.TabularInline):
    """Inline for District within Country"""
    model = District
    extra = 0
    fields = ['name', 'sigla', 'total_deputies', 'district_type']
    ordering = ['name']


# ============================================
# MODEL ADMIN CLASSES
# ============================================

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    """Admin configuration for Agent model"""
    list_display = ['id', 'user', 'full_name', 'email', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    full_name.short_description = 'Full Name'
    
    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    """Admin configuration for Country model"""
    list_display = ['id', 'name', 'code', 'total_deputies', 'districts_count', 'vote_tables_count']
    list_filter = ['total_deputies']
    search_fields = ['name', 'code']
    readonly_fields = []
    ordering = ['name']
    inlines = [DistrictInline]
    fieldsets = (
        ('Country Information', {
            'fields': ('name', 'code', 'total_deputies')
        }),
    )
    
    def districts_count(self, obj):
        return obj.districts.count()
    districts_count.short_description = 'Districts'
    
    def vote_tables_count(self, obj):
        return VoteTable.objects.filter(circunscricao__district__country=obj).count()
    vote_tables_count.short_description = 'Vote Tables'


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    """Admin configuration for District model"""
    list_display = ['id', 'name', 'sigla', 'country', 'district_type', 'total_deputies', 
                    'circunscricoes_count', 'vote_tables_count']
    list_filter = ['country', 'district_type', 'total_deputies']
    search_fields = ['name', 'sigla', 'country__name']
    autocomplete_fields = ['country']
    ordering = ['country', 'name']
    inlines = [CircunscricaoInline]
    fieldsets = (
        ('District Information', {
            'fields': ('name', 'sigla', 'country', 'district_type', 'total_deputies')
        }),
    )
    
    def circunscricoes_count(self, obj):
        return obj.circunscricoes.count()
    circunscricoes_count.short_description = 'Circunscrições'
    
    def vote_tables_count(self, obj):
        return VoteTable.objects.filter(circunscricao__district=obj).count()
    vote_tables_count.short_description = 'Vote Tables'


@admin.register(Circunscricao)
class CircunscricaoAdmin(admin.ModelAdmin):
    """Admin configuration for Circunscricao model"""
    list_display = ['id', 'code', 'name', 'district', 'polling_stations_count', 
                    'vote_tables_count', 'total_voters']
    list_filter = ['district__country', 'district']
    search_fields = ['code', 'name', 'district__name']
    autocomplete_fields = ['district']
    ordering = ['code']
    inlines = [PollingStationInline, VoteTableInline]
    fieldsets = (
        ('Circunscrição Information', {
            'fields': ('code', 'name', 'district')
        }),
    )
    
    def polling_stations_count(self, obj):
        return obj.polling_stations.count()
    polling_stations_count.short_description = 'Polling Stations'
    
    def vote_tables_count(self, obj):
        return obj.vote_tables.count()
    vote_tables_count.short_description = 'Vote Tables'
    
    def total_voters(self, obj):
        total = obj.vote_tables.aggregate(total=Sum('total_voters'))['total'] or 0
        return total
    total_voters.short_description = 'Total Voters'


@admin.register(PollingStation)
class PollingStationAdmin(admin.ModelAdmin):
    """Admin configuration for PollingStation model"""
    list_display = ['id', 'name', 'circunscricao', 'district', 'country', 'vote_tables_count']
    list_filter = ['circunscricao__district__country', 'circunscricao__district']
    search_fields = ['name', 'circunscricao__code']
    autocomplete_fields = ['circunscricao']
    ordering = ['name']
    fieldsets = (
        ('Polling Station Information', {
            'fields': ('name', 'circunscricao')
        }),
    )
    
    def district(self, obj):
        return obj.circunscricao.district
    district.short_description = 'District'
    
    def country(self, obj):
        return obj.circunscricao.district.country
    country.short_description = 'Country'
    
    def vote_tables_count(self, obj):
        return obj.vote_tables.count()
    vote_tables_count.short_description = 'Vote Tables'


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    """Admin configuration for Party model"""
    list_display = ['id', 'name', 'abbreviation', 'color_display', 'is_active', 
                    'created_at', 'vote_entries_count']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['name', 'abbreviation']
    ordering = ['name']
    fieldsets = (
        ('Party Information', {
            'fields': ('name', 'abbreviation', 'color', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 3px 10px; border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = 'Color'
    
    def vote_entries_count(self, obj):
        return obj.vote_entries.count()
    vote_entries_count.short_description = 'Vote Entries'


@admin.register(VoteTable)
class VoteTableAdmin(admin.ModelAdmin):
    """Admin configuration for VoteTable model"""
    list_display = ['id', 'code', 'circunscricao', 'polling_station', 'total_voters',
                    'valid_votes', 'invalid_votes', 'blank_votes', 'votes_cast', 
                    'turnout_percentage', 'recorded_at']
    list_filter = ['circunscricao__district__country', 'circunscricao__district', 
                   'recorded_at']
    search_fields = ['code', 'circunscricao__code', 'polling_station__name', 'location_details']
    autocomplete_fields = ['circunscricao', 'polling_station']
    ordering = ['-recorded_at', 'code']
    inlines = [VoteEntryInline]
    readonly_fields = ['recorded_at', 'updated_at']
    fieldsets = (
        ('Vote Table Information', {
            'fields': ('code', 'circunscricao', 'polling_station', 'location_details')
        }),
        ('Vote Statistics', {
            'fields': ('total_voters', 'valid_votes', 'invalid_votes', 'blank_votes')
        }),
        ('Timestamps', {
            'fields': ('recorded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def votes_cast(self, obj):
        total = obj.vote_entries.aggregate(total=Sum('votes_count'))['total'] or 0
        return total
    votes_cast.short_description = 'Votes Cast'
    
    def turnout_percentage(self, obj):
        total_votes = obj.vote_entries.aggregate(total=Sum('votes_count'))['total'] or 0
        if obj.total_voters > 0:
            percentage = (total_votes / obj.total_voters) * 100
            return percentage
            # return format_html('<span style="font-weight: bold;">{:.1f}%</span>', percentage)
        return '0%'
    turnout_percentage.short_description = 'Turnout'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('vote_entries')


@admin.register(VoteEntry)
class VoteEntryAdmin(admin.ModelAdmin):
    """Admin configuration for VoteEntry model"""
    list_display = ['id', 'vote_table', 'party', 'party_abbreviation', 'votes_count', 
                    'recorded_at', 'updated_at']
    list_filter = ['party', 'recorded_at', 'vote_table__circunscricao__district__country']
    search_fields = ['vote_table__code', 'party__name', 'party__abbreviation']
    autocomplete_fields = ['vote_table', 'party']
    ordering = ['-recorded_at', 'vote_table', '-votes_count']
    fieldsets = (
        ('Vote Entry Information', {
            'fields': ('vote_table', 'party', 'votes_count')
        }),
        ('Timestamps', {
            'fields': ('recorded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['recorded_at', 'updated_at']
    
    def party_abbreviation(self, obj):
        return obj.party.abbreviation
    party_abbreviation.short_description = 'Abbreviation'
    party_abbreviation.admin_order_field = 'party__abbreviation'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('party', 'vote_table')


# ============================================
# RESULTS AND DEPUTIES ADMIN
# ============================================

@admin.register(ResultPerCountryPerParty)
class ResultPerCountryPerPartyAdmin(admin.ModelAdmin):
    """Admin for results per country per party"""
    list_display = ['id', 'country', 'party', 'result']
    list_filter = ['country', 'party']
    search_fields = ['country__name', 'party__name']
    autocomplete_fields = ['country', 'party']
    ordering = ['country', 'party']
    fieldsets = (
        ('Result Information', {
            'fields': ('country', 'party', 'result')
        }),
    )


@admin.register(ResultPerDistrictPerParty)
class ResultPerDistrictPerPartyAdmin(admin.ModelAdmin):
    """Admin for results per district per party"""
    list_display = ['id', 'district', 'party', 'result']
    list_filter = ['district__country', 'district', 'party']
    search_fields = ['district__name', 'party__name']
    autocomplete_fields = ['district', 'party']
    ordering = ['district', 'party']
    fieldsets = (
        ('Result Information', {
            'fields': ('district', 'party', 'result')
        }),
    )


@admin.register(ResultPerCircunscricaoPerParty)
class ResultPerCircunscricaoPerPartyAdmin(admin.ModelAdmin):
    """Admin for results per circunscricao per party"""
    list_display = ['id', 'circunscricao', 'party', 'result']
    list_filter = ['circunscricao__district__country', 'circunscricao__district', 'party']
    search_fields = ['circunscricao__code', 'party__name']
    autocomplete_fields = ['circunscricao', 'party']
    ordering = ['circunscricao', 'party']
    fieldsets = (
        ('Result Information', {
            'fields': ('circunscricao', 'party', 'result')
        }),
    )


@admin.register(DeputiesPerCountryPerParty)
class DeputiesPerCountryPerPartyAdmin(admin.ModelAdmin):
    """Admin for deputies per country per party"""
    list_display = ['id', 'country', 'party', 'deputies']
    list_filter = ['country', 'party']
    search_fields = ['country__name', 'party__name']
    autocomplete_fields = ['country', 'party']
    ordering = ['country', 'party', '-deputies']
    fieldsets = (
        ('Deputies Information', {
            'fields': ('country', 'party', 'deputies')
        }),
    )


@admin.register(DeputiesPerDistrictPerParty)
class DeputiesPerDistrictPerPartyAdmin(admin.ModelAdmin):
    """Admin for deputies per district per party"""
    list_display = ['id', 'district', 'party', 'deputies']
    list_filter = ['district__country', 'district', 'party']
    search_fields = ['district__name', 'party__name']
    autocomplete_fields = ['district', 'party']
    ordering = ['district', 'party', '-deputies']
    fieldsets = (
        ('Deputies Information', {
            'fields': ('district', 'party', 'deputies')
        }),
    )


# ============================================
# CUSTOM ADMIN VIEWS (OPTIONAL)
# ============================================

class VoteSummaryAdmin(admin.ModelAdmin):
    """Custom admin for vote summary - not registered by default"""
    change_list_template = 'admin/vote_summary_change_list.html'
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Aggregate statistics
        total_voters = VoteTable.objects.aggregate(total=Sum('total_voters'))['total'] or 0
        total_votes = VoteEntry.objects.aggregate(total=Sum('votes_count'))['total'] or 0
        
        # Results by party
        results_by_party = VoteEntry.objects.values(
            'party__name', 'party__abbreviation', 'party__color'
        ).annotate(
            total_votes=Sum('votes_count')
        ).order_by('-total_votes')
        
        extra_context.update({
            'total_voters': total_voters,
            'total_votes': total_votes,
            'turnout': (total_votes / total_voters * 100) if total_voters > 0 else 0,
            'results_by_party': results_by_party,
            'total_parties': results_by_party.count(),
        })
        
        return super().changelist_view(request, extra_context=extra_context)