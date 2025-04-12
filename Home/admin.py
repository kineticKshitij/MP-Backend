from django.contrib import admin
from Home.models import Organization, EmployeeSignup, Query, RFIDCard, Attendance

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email')
    search_fields = ('name', 'email')
    list_filter = ('name',)
    ordering = ('id',)
    actions = ['custom_delete_selected']

    def custom_delete_selected(self, request, queryset):
        # Delete objects without creating deletion LogEntry records.
        queryset.delete()
    custom_delete_selected.short_description = "Delete selected Organizations (without logging)"

@admin.register(EmployeeSignup)
class EmployeeSignupAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'organization']
    search_fields = ['name', 'email']
    list_filter = ['organization']
    ordering = ['-id']  # Use ID for ordering instead of date

@admin.register(Query)
class QueryAdmin(admin.ModelAdmin):
    list_display = ('subject', 'organization', 'status', 'created_at')
    list_filter = ('status', 'organization', 'created_at')
    search_fields = ('subject', 'description')
    ordering = ('-created_at',)
    
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('subject', 'description', 'organization')
        }),
        ('Status Information', {
            'fields': ('status', ('created_at', 'updated_at'))
        }),
    )

@admin.register(RFIDCard)
class RFIDCardAdmin(admin.ModelAdmin):
    list_display = ("card_uid", "scanned_at")
    search_fields = ("card_uid",)