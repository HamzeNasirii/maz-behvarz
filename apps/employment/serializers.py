from rest_framework import serializers

from .models import EmploymentAssignment


class EmploymentAssignmentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    health_house_name = serializers.CharField(source="health_house.name", read_only=True)

    class Meta:
        model = EmploymentAssignment
        fields = [
            "id", "username", "health_house_name", "employment_type",
            "start_date", "end_date", "is_active", "is_primary", "approval_status",
        ]