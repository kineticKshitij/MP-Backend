from django.db.backends.base.operations import BaseDatabaseOperations
from djongo.operations import DatabaseOperations

class DjongoDateOperations(BaseDatabaseOperations):
    def datetime_trunc_sql(self, lookup_type, field_name, tzname=None):
        # Basic implementation for MongoDB date truncation
        if lookup_type == 'year':
            return f"datetime(year({field_name}), 1, 1)", []
        elif lookup_type == 'month':
            return f"datetime(year({field_name}), month({field_name}), 1)", []
        elif lookup_type == 'day':
            return f"datetime(year({field_name}), month({field_name}), day({field_name}))", []
        return field_name, []

class CustomDatabaseOperations(DatabaseOperations):
    def datetime_trunc_sql(self, lookup_type, field_name, tzname=None):
        field_name = f'"{field_name}"'
        trunc_mapping = {
            'year': {'$year': field_name},
            'month': {'$month': field_name},
            'day': {'$dayOfMonth': field_name},
            'hour': {'$hour': field_name},
            'minute': {'$minute': field_name}
        }
        return trunc_mapping.get(lookup_type, field_name), []

    def get_db_converters(self, expression):
        converters = super().get_db_converters(expression)
        return converters