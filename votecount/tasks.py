from asgiref.sync import async_to_sync
from celery import shared_task
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
    VoteTable,
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
            {"type": type_name, "data": data["results"]},
        )
        return True
    except Exception as e:
        print(f"Failed to broadcast to group {group_name}: {e!s}")
        return False


def broadcast_to_all_groups(channel_layer, type_name, data):
    """data is the payload dict; we send it under the 'data' key."""
    groups = ["citizen", "admin", "agent"]

    if data.get("country_id"):
        groups.append(f"result_country_{data['country_id']}")
    if data.get("district_id"):
        groups.append(f"result_district_{data['district_id']}")
    if data.get("circunscricao_id"):
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
        "type": "result_country",
        "country_id": country_id,
        "results": NestedCountrySerializer(country).data,
    }
    broadcast_to_all_groups(channel_layer, "result_country", payload)


def broadcast_result_per_district(district_id, channel_layer=None):
    from .serializers import NestedDistrictSerializer

    channel_layer = channel_layer or get_channel_layer()

    district = District.objects.select_related("country").get(id=district_id)
    payload = {
        "type": "result_district",
        "district_id": district_id,
        "results": NestedDistrictSerializer(district).data,
    }
    broadcast_to_all_groups(channel_layer, "result_district", payload)


def broadcast_result_per_circunscricao(circunscricao_id, channel_layer=None):
    from .serializers import NestedCircunscricaoSerializer

    channel_layer = channel_layer or get_channel_layer()

    circ = Circunscricao.objects.select_related("district__country").get(
        id=circunscricao_id
    )
    payload = {
        "type": "result_circunscricao",
        "circunscricao_id": circunscricao_id,
        "results": NestedCircunscricaoSerializer(circ).data,
    }
    broadcast_to_all_groups(channel_layer, "result_circunscricao", payload)


# ---- Main task ---------------------------------------------------------


@shared_task
def aggregate_votetable_results_task(vote_table_id):
    """
    Processes all tiers of election calculations at the VoteTable level.
    Guarantees zero deadlocks by sorting all bulk-updates by primary key.
    """
    channel_layer = get_channel_layer()

    try:
        # 1. Fetch metadata and anchor rows deterministically via select_for_update
        with transaction.atomic():
            try:
                vote_table = (
                    VoteTable.objects.select_for_update()
                    .select_related("circunscricao__district__country")
                    .get(id=vote_table_id)
                )
            except VoteTable.DoesNotExist:
                return f"VoteTable {vote_table_id} not found."

            circunscricao = vote_table.circunscricao
            district = circunscricao.district
            country = district.country

            # ==========================================
            # 1. CIRCUNSCRIÇÃO LEVEL PROCESS
            # ==========================================
            circ_rows = (
                VoteEntry.objects.filter(vote_table__circunscricao=circunscricao)
                .values("party_id")
                .annotate(total=Sum("votes_count"))
            )

            # SORT by party_id to prevent deadlocks across rows
            sorted_circ_rows = sorted(circ_rows, key=lambda x: x["party_id"])

            for row in sorted_circ_rows:
                ResultPerCircunscricaoPerParty.objects.update_or_create(
                    circunscricao=circunscricao,
                    party_id=row["party_id"],
                    defaults={"result": row["total"]},
                )

            # ==========================================
            # 2. DISTRICT LEVEL PROCESS & SEAT ALLOCATION
            # ==========================================
            is_diaspora = district.district_type in [
                "DIASPORA_EUROPE",
                "DIASPORA_AFRICA",
            ]

            if is_diaspora:
                total_seats = 1
                district_votes_query = (
                    VoteEntry.objects.filter(
                        vote_table__circunscricao__district__district_type=district.district_type
                    )
                    .values("party_id")
                    .annotate(total=Sum("votes_count"))
                )
            else:
                total_seats = district.total_deputies
                district_votes_query = (
                    VoteEntry.objects.filter(
                        vote_table__circunscricao__district=district
                    )
                    .values("party_id")
                    .annotate(total=Sum("votes_count"))
                )

            dist_votes = {
                r["party_id"]: r["total"]
                for r in district_votes_query
                if r["total"] > 0
            }
            district_seats = run_dhondt(dist_votes, total_seats)

            # SORT keys to enforce strict database row locking sequences
            sorted_party_ids = sorted(dist_votes.keys())

            for party_id in sorted_party_ids:
                total = dist_votes[party_id]

                if is_diaspora:
                    specific_total = (
                        VoteEntry.objects.filter(
                            vote_table__circunscricao__district=district,
                            party_id=party_id,
                        ).aggregate(t=Sum("votes_count"))["t"]
                        or 0
                    )
                else:
                    specific_total = total

                ResultPerDistrictPerParty.objects.update_or_create(
                    district=district,
                    party_id=party_id,
                    defaults={
                        "result": specific_total,
                        "deputies": district_seats.get(party_id, 0),
                    },
                )

            # ==========================================
            # 3. COUNTRY LEVEL PROCESS
            # ==========================================
            country_votes_query = (
                VoteEntry.objects.filter(
                    vote_table__circunscricao__district__country=country
                )
                .values("party_id")
                .annotate(total=Sum("votes_count"))
            )
            sorted_country_rows = sorted(
                country_votes_query, key=lambda x: x["party_id"]
            )

            country_seats_query = (
                ResultPerDistrictPerParty.objects.filter(district__country=country)
                .values("party_id")
                .annotate(total_seats_won=Sum("deputies"))
            )
            country_seats_map = {
                m["party_id"]: m["total_seats_won"] for m in country_seats_query
            }

            for row in sorted_country_rows:
                p_id = row["party_id"]
                ResultPerCountryPerParty.objects.update_or_create(
                    country=country,
                    party_id=p_id,
                    defaults={
                        "result": row["total"],
                        "deputies": country_seats_map.get(p_id, 0),
                    },
                )

        # ==========================================
        # 4. BROADCASTS (Executed OUTSIDE the DB Transaction)
        # ==========================================
        broadcast_result_per_circunscricao(circunscricao.id, channel_layer)
        broadcast_result_per_district(district.id, channel_layer)
        broadcast_result_per_country(country.id, channel_layer)

        return f"Successfully processed and broadcasted VoteTable {vote_table_id}"

    except Exception as e:
        try:
            broadcast_result_update(
                channel_layer,
                "admin",
                "error",
                {"message": str(e), "vote_table_id": vote_table_id},
            )
        except Exception:
            pass
        raise
