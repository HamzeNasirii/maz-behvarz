from rest_framework import serializers

from .models import Member, MembershipPeriod


class MembershipPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipPeriod
        fields = ["id", "start_date", "end_date", "is_active", "reason"]


class MemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.SerializerMethodField()
    membership_periods = MembershipPeriodSerializer(many=True, read_only=True)

    class Meta:
        model = Member
        fields = [
            "id", "username", "full_name", "membership_number",
            "approval_status", "membership_periods",
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username