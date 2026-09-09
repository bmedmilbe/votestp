from django.db import transaction
from django.db.models import Sum

from .models import (
    DeputiesPerCountryPerParty,
    DeputiesPerDistrictPerParty,
    ResultPerCircunscricaoPerParty,
    ResultPerCountryPerParty,
    ResultPerDistrictPerParty,
    VoteEntry,
)


def run_dhondt(votes_dict, total_seats):
    seats_alloc = {party_id: 0 for party_id in votes_dict}
    if not votes_dict or total_seats <= 0:
        return seats_alloc
    
    for _ in range(total_seats):
        best_party = None
        max_quotient = -1.0
        for party_id, total_votes in votes_dict.items():
            quotient = float(total_votes) / (seats_alloc[party_id] + 1)
            if quotient > max_quotient:
                max_quotient = quotient
                best_party = party_id
        if best_party is not None:
            seats_alloc[best_party] += 1
    return seats_alloc

# @shared_task(bind=True, max_retries=3, default_retry_delay=5)
# def sum_vote_entry_task(self, vote_entry_id):
def sum_vote_entry_task( vote_entry_id):
    try:
        # Use select_for_update to prevent race conditions on the root entry
        with transaction.atomic():
            try:
                entry = VoteEntry.objects.select_for_update().get(id=vote_entry_id)
            except VoteEntry.DoesNotExist:
                return f"VoteEntry {vote_entry_id} not found."

            vote_table = entry.vote_table
            circunscricao = vote_table.circunscricao
            district = circunscricao.district
            country = district.country

            # 1. Update ResultPerCircunscricaoPerParty
            circ_votes = VoteEntry.objects.filter(vote_table__circunscricao=circunscricao) \
                .values('party_id').annotate(total=Sum('votes_count'))
            for row in circ_votes:
                ResultPerCircunscricaoPerParty.objects.update_or_create(
                    circunscricao=circunscricao, party_id=row['party_id'],
                    defaults={'result': row['total']}
                )

            # 2. Update ResultPerDistrictPerParty
            dist_votes = VoteEntry.objects.filter(vote_table__circunscricao__district=district) \
                .values('party_id').annotate(total=Sum('votes_count'))
            dist_votes_dict = {}
            for row in dist_votes:
                ResultPerDistrictPerParty.objects.update_or_create(
                    district=district, party_id=row['party_id'],
                    defaults={'result': row['total']}
                )
                dist_votes_dict[row['party_id']] = row['total']

            # 3. Update ResultPerCountryPerParty
            country_votes = VoteEntry.objects.filter(vote_table__circunscricao__district__country=country) \
                .values('party_id').annotate(total=Sum('votes_count'))
            country_votes_dict = {}
            for row in country_votes:
                ResultPerCountryPerParty.objects.update_or_create(
                    country=country, party_id=row['party_id'],
                    defaults={'result': row['total']}
                )
                country_votes_dict[row['party_id']] = row['total']

            # 4. Calculate & Update DeputiesPerDistrictPerParty
            district_seats_allocation = run_dhondt(dist_votes_dict, district.total_deputies)
            for party_id, seats in district_seats_allocation.items():
                DeputiesPerDistrictPerParty.objects.update_or_create(
                    district=district, party_id=party_id,
                    defaults={'deputies': seats}
                )

            # 5. Calculate & Update DeputiesPerCountryPerParty
            country_seats_allocation = run_dhondt(country_votes_dict, country.total_deputies)
            for party_id, seats in country_seats_allocation.items():
                DeputiesPerCountryPerParty.objects.update_or_create(
                    country=country, party_id=party_id,
                    defaults={'deputies': seats}
                )
                
            return f"Successfully recalculated results for entry {vote_entry_id}"
            
    except Exception:
        # Retry task if database locking or network glitches occur
        # rai#se self.retry(exc=exc)
        pass
