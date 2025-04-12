from rest_framework import serializers
from Home.models import EmployeeSignup, Query, Organization

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