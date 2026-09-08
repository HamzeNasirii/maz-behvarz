from rest_framework import serializers

from .models import MembershipApplication


class MembershipApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipApplication
        fields = [
            "full_name", "national_code", "mobile_number", "health_house", "accepted_terms",
        ]

    def validate_accepted_terms(self, value):
        if not value:
            raise serializers.ValidationError("پذیرش تعهدنامه الزامی است.")
        return value