from django.contrib import admin

from .models import *


# Register Agent separately if needed (optional)
@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    """
    Separate admin for Agent if needed.
    """

    list_display = ("email", "created_at", "updated_at")
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "updated_at")

    def email(self, obj):
        return obj.user.email

    email.short_description = "Email"



@admin.register(Circunscricao)
class CircunscricaoAdmin(admin.ModelAdmin):
    list_display = ['code', 'district', 'name']
    search_fields = ['code', 'name']
    list_filter = ['district']

@admin.register(PollingStation)
class PollingStationAdmin(admin.ModelAdmin):
    list_display = ['name', 'circunscricao']
    search_fields = ['name']
    list_filter = ['circunscricao']

@admin.register(VoteTable)
class VoteTableAdmin(admin.ModelAdmin):
    list_display = ['code', 'circunscricao', 'total_voters', 'valid_votes']
    list_filter = ['circunscricao']
    search_fields = ['code', 'location_details']

@admin.register(VoteEntry)
class VoteEntryAdmin(admin.ModelAdmin):
    list_display = ['vote_table', 'party', 'votes_count']
    list_filter = ['vote_table__circunscricao', 'party']
    search_fields = ['vote_table__code', 'party__name']

@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ['name', 'abbreviation', 'color', 'is_active']
    search_fields = ['name', 'abbreviation']
    list_filter = ['is_active']

@admin.register(VoteResult)
class VoteResultAdmin(admin.ModelAdmin):
    list_display = ['result_type', 'party', 'total_votes', 'deputies_allocated']
    list_filter = ['result_type', 'party']
    search_fields = ['party__name']

@admin.register(HondtCalculation)
class HondtCalculationAdmin(admin.ModelAdmin):
    list_display = ['district', 'party', 'deputies_allocated', 'calculation_round']
    list_filter = ['district', 'party']
    search_fields = ['district__name', 'party__name']

@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'total_deputies']
    list_filter = ['country']
    search_fields = ['name']

@admin.register(ElectionStats)
class ElectionStatsAdmin(admin.ModelAdmin):
    list_display = ['country', 'total_voters', 'voter_turnout', 'calculated_at']
    list_filter = ['country']
