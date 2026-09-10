from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Sum

from .models import (
    Circunscricao,
    Country,
    District,
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


def broadcast_result_update(channel_layer, group_name, type_name, data):
    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {'type': type_name, 'data': data['results']},
        )
        return True
    except Exception as e:
        print(f"Failed to broadcast to group {group_name}: {e!s}")
        return False


def broadcast_to_all_groups(channel_layer, type_name, data):
    """data is the payload dict; we send it under the 'data' key."""
    groups = ['citizen', 'admin', 'agent']

    if data.get('country_id'):
        groups.append(f"result_country_{data['country_id']}")
    if data.get('district_id'):
        groups.append(f"result_district_{data['district_id']}")
    if data.get('circunscricao_id'):
        groups.append(f"result_circunscricao_{data['circunscricao_id']}")

    for group in groups:
        # send the whole payload as 'data'
        broadcast_result_update(channel_layer, group, type_name, data)


# ---- Individual broadcasters (NO async decorator!) --------------------

def broadcast_result_per_country(country_id, channel_layer=None):
    from .serializers import NestedCountrySerializer
    channel_layer = channel_layer or get_channel_layer()

    country = Country.objects.get(id=country_id)
    payload = {
        'type': 'result_country',
        'country_id': country_id,
        'results': NestedCountrySerializer(country).data,
    }
    broadcast_to_all_groups(channel_layer, 'result_country', payload)


def broadcast_result_per_district(district_id, channel_layer=None):
    from .serializers import NestedDistrictSerializer
    channel_layer = channel_layer or get_channel_layer()

    district = District.objects.select_related('country').get(id=district_id)
    payload = {
        'type': 'result_district',
        'district_id': district_id,
        'results': NestedDistrictSerializer(district).data,
    }
    broadcast_to_all_groups(channel_layer, 'result_district', payload)


def broadcast_result_per_circunscricao(circunscricao_id, channel_layer=None):
    from .serializers import NestedCircunscricaoSerializer
    channel_layer = channel_layer or get_channel_layer()

    circ = Circunscricao.objects.select_related('district__country').get(id=circunscricao_id)
    payload = {
        'type': 'result_circunscricao',
        'circunscricao_id': circunscricao_id,
        'results': NestedCircunscricaoSerializer(circ).data,
    }
    broadcast_to_all_groups(channel_layer, 'result_circunscricao', payload)


# ---- Main task ---------------------------------------------------------

def sum_vote_entry_task(vote_entry_id):
    try:
        with transaction.atomic():
            try:
                entry = VoteEntry.objects.select_for_update().get(id=vote_entry_id)
            except VoteEntry.DoesNotExist:
                msg = f"VoteEntry {vote_entry_id} not found."
                broadcast_result_update(
                    get_channel_layer(), 'admin', 'error', {'message': msg}
                )
                return msg

            vote_table    = entry.vote_table
            circunscricao = vote_table.circunscricao
            district      = circunscricao.district
            country       = district.country
            channel_layer = get_channel_layer()

            # 1. ResultPerCircunscricaoPerParty
            for row in (VoteEntry.objects
                        .filter(vote_table__circunscricao=circunscricao)
                        .values('party_id').annotate(total=Sum('votes_count'))):
                ResultPerCircunscricaoPerParty.objects.update_or_create(
                    circunscricao=circunscricao, party_id=row['party_id'],
                    defaults={'result': row['total']},
                )


            # ==========================================
            # 1. DISTRICT LEVEL PROCESS & SEAT ALLOCATION
            # ==========================================
            is_diaspora = district.district_type in ['DIASPORA_EUROPE', 'DIASPORA_AFRICA']

            if is_diaspora:
                # Diaspora blocks share exactly 1 seat across all their countries
                total_seats = 1
                # Aggregate votes across ALL districts in this global diaspora block
                district_votes_query = (
                    VoteEntry.objects
                    .filter(vote_table__circunscricao__district__district_type=district.district_type)
                    .values('party_id')
                    .annotate(total=Sum('votes_count'))
                )
            else:
                # Standard districts use their own total_deputies
                total_seats = district.total_deputies
                district_votes_query = (
                    VoteEntry.objects
                    .filter(vote_table__circunscricao__district=district)
                    .values('party_id')
                    .annotate(total=Sum('votes_count'))
                )

            # Calculate D'Hondt seats for the district tier
            dist_votes = {r['party_id']: r['total'] for r in district_votes_query if r['total'] > 0}
            district_seats = run_dhondt(dist_votes, total_seats)

            # Upsert District results
            for party_id, total in dist_votes.items():
                # If diaspora, calculate this specific district's isolated vote share for display
                if is_diaspora:
                    specific_total = (
                        VoteEntry.objects
                        .filter(vote_table__circunscricao__district=district, party_id=party_id)
                        .aggregate(t=Sum('votes_count'))['t'] or 0
                    )
                else:
                    specific_total = total

                ResultPerDistrictPerParty.objects.update_or_create(
                    district=district,
                    party_id=party_id,
                    defaults={
                        'result': specific_total,
                        'deputies': district_seats.get(party_id, 0) 
                    },
                )


            # ==========================================
            # 2. COUNTRY LEVEL PROCESS (SUM OF DISTRICTS)
            # ==========================================
            # Step A: Get total votes cast in this country
            country_votes_query = (
                VoteEntry.objects
                .filter(vote_table__circunscricao__district__country=country)
                .values('party_id')
                .annotate(total=Sum('votes_count'))
            )

            # Step B: Sum the actual seats won across all districts belonging to this country
            country_seats_query = (
                ResultPerDistrictPerParty.objects
                .filter(district__country=country)
                .values('party_id')
                .annotate(total_seats_won=Sum('deputies'))
            )
            country_seats_map = {m['party_id']: m['total_seats_won'] for m in country_seats_query}

            # Step C: Write combined data to Country tier
            for row in country_votes_query:
                party_id = row['party_id']
                ResultPerCountryPerParty.objects.update_or_create(
                    country=country,
                    party_id=party_id,
                    defaults={
                        'result': row['total'],
                        'deputies': country_seats_map.get(party_id, 0) # Summed up from districts
                    },
                )


            # ==========================================
            # 3. BROADCASTS
            # ==========================================
            broadcast_result_per_circunscricao(circunscricao.id, channel_layer)
            broadcast_result_per_district(district.id, channel_layer)
            broadcast_result_per_country(country.id, channel_layer)



            return f"Successfully recalculated and broadcasted results for entry {vote_entry_id}"

    except Exception as e:
        try:
            broadcast_result_update(
                get_channel_layer(), 'admin', 'error',
                {'message': str(e), 'vote_entry_id': vote_entry_id},
            )
        except Exception:
            pass
        raise