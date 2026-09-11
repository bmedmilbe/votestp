# services.py
from votecount.models import HondtCalculation, VoteEntry, VoteResult


class HondtMethodService:
    """Service to implement the Hondt method for deputy allocation"""

    def __init__(self, district, total_seats):
        self.district = district
        self.total_seats = total_seats
        self.party_votes = {}
        self.results = {}

    def calculate_party_votes(self):
        """Get total votes per party for a district"""
        # Aggregate votes from all vote tables in the district
        from django.db.models import Sum

        votes = (
            VoteEntry.objects.filter(vote_table__circunscricao__district=self.district)
            .values("party")
            .annotate(total=Sum("votes_count"))
        )

        for vote in votes:
            self.party_votes[vote["party"]] = vote["total"]

        return self.party_votes

    def allocate_deputies(self):
        """Allocate deputies using the Hondt method"""
        self.calculate_party_votes()

        # Initialize results dictionary
        for party_id in self.party_votes:
            self.results[party_id] = 0

        # For each seat, find the party with the highest quotient
        for _ in range(self.total_seats):
            max_quotient = 0
            selected_party = None

            for party_id, total_votes in self.party_votes.items():
                allocated = self.results[party_id]
                if allocated == 0:
                    quotient = total_votes
                else:
                    quotient = total_votes / (allocated + 1)

                if quotient > max_quotient:
                    max_quotient = quotient
                    selected_party = party_id

            if selected_party:
                self.results[selected_party] += 1

        # Save results to database
        self._save_results()

        return self.results

    def _save_results(self):
        """Save Hondt calculation results to database"""
        from django.db import transaction

        with transaction.atomic():
            for party_id, deputies in self.results.items():
                # Delete old calculations for this district and party
                HondtCalculation.objects.filter(
                    district=self.district, party_id=party_id
                ).delete()

                # Create new calculation record
                HondtCalculation.objects.create(
                    district=self.district,
                    party_id=party_id,
                    total_votes=self.party_votes[party_id],
                    deputies_allocated=deputies,
                )

                # Update VoteResult for this district and party
                VoteResult.objects.update_or_create(
                    result_type="DISTRICT",
                    party_id=party_id,
                    district=self.district,
                    defaults={
                        "deputies_allocated": deputies,
                        "total_votes": self.party_votes[party_id],
                    },
                )
