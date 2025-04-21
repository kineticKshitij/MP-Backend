from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    # Organization views
    organization_signup, 
    organization_login,
    organization_dashboard,
    
    # Employee views
    employee_login,
    employee_dashboard,
    add_employee, 
    manage_employees, 
    remove_employee,
    mark_employee_attendance,
    
    # Query views
    submit_query, 
    get_public_queries,
    index,
    receive_rfid,

    # Attendance views
    get_monthly_attendance,
    get_server_time,
)

# API URL patterns by domain
organization_patterns = [
    path('signup/', organization_signup, name='organization_signup'),
    path('login/', organization_login, name='organization_login'),
    path('dashboard/', organization_dashboard, name='organization_dashboard'),
]

employee_patterns = [
    path('login/', employee_login, name='employee_login'),
    path('dashboard/', employee_dashboard, name='employee_dashboard'),
    path('add-employee/<str:company>/', add_employee, name='add_employee'),
    path('manage/', manage_employees, name='manage_employees'),
    path('remove/<int:employee_id>/', remove_employee, name='remove_employee'),
    path("attendance/monthly/<int:year>/<int:month>/", get_monthly_attendance, name="get_monthly_attendance"),
    path("attendance/mark/<int:employee_id>/<str:status_>/", mark_employee_attendance, name="mark_employee_attendance"),
]

query_patterns = [
    path('submit/', submit_query, name='submit_query'),
    path('public/', get_public_queries, name='get_public_queries'),
]


urlpatterns = [
    # JWT endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API endpoints grouped by domain
    path('api/org/', include(organization_patterns)),
    path('api/emp/', include(employee_patterns)),
    path('api/query/', include(query_patterns)),
    path('api/rfid/scan/', receive_rfid, name='receive_rfid'),
    re_path(r'^api/rfid/scan$', receive_rfid),
    path("api/time/", get_server_time, name="get_server_time"),
    # Root index view
    path('', index, name='index'),
]

# Development-only URLs
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
