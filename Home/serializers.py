from rest_framework import serializers
from Home.models import EmployeeSignup, Query, Organization
from .models import Attendance

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeSignup
        fields = '__all__'

class ContactQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Query
        fields = '__all__'

class OrganizationSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ['id', 'name', 'email', 'logo']

    def get_logo(self, obj):
        request = self.context.get('request')
        if obj.logo:
            return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url
        return None

class AttendanceSerializer(serializers.ModelSerializer):
    employee_unique_id = serializers.CharField(source="employee.unique_id")
    employee_name = serializers.CharField(source="employee.name")
    # Format check_in to a simple time string (use your preferred format)
    check_in = serializers.DateTimeField(format="%H:%M:%S", required=False, allow_null=True)
    # Format date as YYYY-MM-DD
    date = serializers.DateField(format="%Y-%m-%d")
    
    class Meta:
        model = Attendance
        fields = ["employee_unique_id", "employee_name", "check_in", "date", "status"]