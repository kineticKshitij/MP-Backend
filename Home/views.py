import logging
import traceback
from datetime import datetime, time as dt_time, timedelta, date
import threading
import json
from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.images import get_image_dimensions
from django.utils import timezone
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.decorators import (
    api_view, permission_classes, parser_classes, throttle_classes
)
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from calendar import monthrange
from pymongo import MongoClient
from .models import Organization, EmployeeSignup, Query, Attendance
from .serializers import OrganizationSerializer, EmployeeSerializer, ContactQuerySerializer
import calendar
# Configure logging
logger = logging.getLogger(__name__)

# Global variables for attendance tracking
attendance_records = []
attendance_lock = threading.Lock()

# Time configuration for email notifications
EMAIL_SEND_TIME = dt_time(16, 39)  # 4:39 PM

def send_attendance_email():
    """Background thread function to send attendance emails."""
    while True:
        try:
            current_time = timezone.localtime().time()
            
            # Check if it's time to send emails
            if (current_time.hour == EMAIL_SEND_TIME.hour and 
                current_time.minute == EMAIL_SEND_TIME.minute):
                
                # Process attendance records
                with attendance_lock:
                    records_to_process = attendance_records.copy()
                    attendance_records.clear()
                
                # Send emails for each record
                for record in records_to_process:
                    try:
                        subject = f"Attendance Confirmation - {record['name']}"
                        message = (
                            f"Employee: {record['name']}\n"
                            f"ID: {record['employee_id']}\n"
                            f"Time: {record['timestamp']}\n"
                            f"Date: {timezone.localtime().strftime('%Y-%m-%d')}"
                        )
                        
                        send_mail(
                            subject=subject,
                            message=message,
                            from_email=settings.EMAIL_HOST_USER,
                            recipient_list=[record['organization_email']],
                            fail_silently=False,
                        )
                        logger.info(f"✉️ Sent attendance email for {record['name']}")
                    except Exception as e:
                        logger.error(f"⚠️ Failed to send email for {record['name']}: {str(e)}")
            
            # Sleep for 60 seconds before next check
            import time
            time.sleep(60)
            
        except Exception as e:
            logger.error(f"⚠️ Email thread error: {str(e)}")
            time.sleep(60)  # Wait before retrying

# Start email thread if email settings are configured
if hasattr(settings, 'EMAIL_HOST_USER') and settings.EMAIL_HOST_USER:
    threading.Thread(target=send_attendance_email, daemon=True).start()
    logger.info("📧 Started attendance email notification thread")

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@parser_classes([JSONParser])
def receive_rfid(request):
    """API endpoint to receive RFID card UID and mark attendance."""
    try:
        # Parse JSON data
        data = json.loads(request.body.decode('utf-8'))
        logger.info(f"🔍 Received RFID data: {data}")

        # Validate card_uid
        card_uid = data.get("card_uid", "").lower().strip()
        if not card_uid:
            return Response({
                "status": "error",
                "message": "Card UID is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        print("Card_UID==>", card_uid)
        
        # Use pymongo directly
        from pymongo import MongoClient
        client = MongoClient('mongodb://localhost:27017/')
        db = client['minor_project_db']
        
        # Find employee using MongoDB query
        employee_data = db.Home_employeesignup.find_one({
            'rfid': card_uid,
            'is_active': True
        })

        if not employee_data:
            client.close()
            return Response({
                "status": "error",
                "message": "Invalid card"
            }, status=status.HTTP_404_NOT_FOUND)

        # Use a unified identifier: if unique_id exists, use it; otherwise, fallback to _id
        employee_identifier = employee_data.get('unique_id', employee_data['_id'])

        # Check for existing attendance
        today = timezone.localtime().date().strftime('%Y-%m-%d')
        existing = db.Home_attendance.find_one({
            'employee_id': employee_identifier,
            'date': today
        })

        if existing:
            client.close()
            return Response({
                "status": "error",
                "message": "Already marked",
                "data": {
                    "employee_name": employee_data['name'],
                    "timestamp": existing.get('timestamp')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create attendance record using the employee's unique_id as primary key
        now = timezone.now()
        attendance_data = {
            'employee_id': employee_identifier,
            'status': 'P',
            'timestamp': now.strftime('%H:%M:%S'),
            'date': today
        }
        
        db.Home_attendance.insert_one(attendance_data)
        client.close()

        # Add to email notification queue
        with attendance_lock:
            attendance_records.append({
                "name": employee_data['name'],
                "employee_id": employee_identifier,
                "timestamp": now.strftime("%H:%M:%S"),
                "organization_email": employee_data['email']
            })

        return Response({
            "status": "success",
            "message": f"Welcome {employee_data['name']}",
            "data": {
                "employee_name": employee_data['name'],
                "employee_id": employee_identifier,
                "timestamp": now.strftime('%H:%M:%S')
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(f"⚠️ RFID processing error: {str(e)}")
        return Response({
            "status": "error",
            "message": "System error",
            "debug_info": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Render index page
def index(request):
    return render(request, "index.html")

# ---------------------------
# Utility Functions
# ---------------------------
def validate_image(image_file):
    if not image_file:
        return None
    if image_file.size > 5 * 1024 * 1024:
        return "Image size must be under 5MB"
    width, height = get_image_dimensions(image_file)
    if width > 2000 or height > 2000:
        return "Image dimensions must be 2000x2000 pixels or smaller"
    allowed_types = ['image/jpeg', 'image/png', 'image/gif']
    if image_file.content_type not in allowed_types:
        return "Image must be JPEG, PNG, or GIF format"
    return None

def validate_credentials(data):
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return "Email and password are required"
    return None

def get_attendance_table(start_date, end_date):
    """
    Generates an attendance table for a given date range.
    :param start_date: Start date of the range
    :param end_date: End date of the range
    :return: A dictionary with employee names as keys and attendance records as values
    """
    employees = EmployeeSignup.objects.all()
    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    attendance_table = {}

    for employee in employees:
        attendance_table[employee.name] = []
        for day in date_range:
            attendance = Attendance.objects.filter(employee=employee, date=day).first()
            if attendance:
                attendance_table[employee.name].append(attendance.timestamp if attendance.status == 'P' else attendance.get_status_display())
            else:
                attendance_table[employee.name].append('A')  # Default to Absent if no record exists

    return attendance_table

# ---------------------------
# Organization Endpoints
# ---------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@throttle_classes([UserRateThrottle])
def organization_signup(request):
    try:
        data = request.data
        print("From Frontend=>", data)
        if not all([data.get('name'), data.get('email'), data.get('password')]):
            return Response({'error': 'Name, email, and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        cred_error = validate_credentials(data)
        if cred_error:
            return Response({'error': cred_error}, status=status.HTTP_400_BAD_REQUEST)

        if Organization.objects.filter(email=data.get('email')).exists():
            return Response({'error': 'Email is already registered'}, status=status.HTTP_400_BAD_REQUEST)

        logo = request.FILES.get('logo')
        if logo:
            logo_error = validate_image(logo)
            if logo_error:
                return Response({'error': logo_error}, status=status.HTTP_400_BAD_REQUEST)

        organization = Organization.objects.create(
            name=data.get('name'),
            email=data.get('email'),
            password=make_password(data.get('password')),
            logo=logo
        )

        return Response({
            'message': 'Organization registered successfully',
            'organization': OrganizationSerializer(organization).data
        }, status=status.HTTP_201_CREATED)
    except Exception:
        logger.error(f"Organization signup error: {traceback.format_exc()}")
        return Response({'error': 'Registration failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------
# JWT Organization Login
# ---------------------------
@api_view(['POST'])
@permission_classes([AllowAny])
def organization_login(request):
    """
    Authenticate an organization using email and password,
    and return JWT tokens on success.
    """
    try:
        data = request.data
        if not data.get('email') or not data.get('password'):
            return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        org = authenticate(request, email=data.get('email'), password=data.get('password'))
        if org is None:
            return Response({'error': 'Invalid email or password'}, status=status.HTTP_400_BAD_REQUEST)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(org)
        return Response({
            'message': 'Login successful',
            'organization': {
                'id': org.id,
                'name': org.name,
                'email': org.email,
            },
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }, status=status.HTTP_200_OK)

    except Exception:
        logger.error(f"Organization login error: {traceback.format_exc()}")
        return Response({'error': 'Login failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------
# Organization Dashboard (JWT Protected)
# ---------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organization_dashboard(request):
    try:
        org = request.user
        
        # Get organization data and counts
        query_count = Query.objects.filter(organization=org).count()
        employee_count = EmployeeSignup.objects.filter(organization=org).count()
        attendance_today = Attendance.objects.filter(
            employee__organization=org,
            date=timezone.now().date()
        ).count()

        # Include complete organization data
        return Response({
            'organization': {
                'id': org.id,
                'name': org.name,
                'email': org.email,
                'logo': request.build_absolute_uri(org.logo.url) if org.logo else None,
            },
            'stats': {
                'query_count': query_count,
                'employee_count': employee_count,
                'attendance_today': attendance_today
            }
        })
    except Exception as e:
        logger.error(f"Organization dashboard error: {traceback.format_exc()}")
        return Response({'error': str(e)}, status=500)


# ---------------------------
# (Optional) JWT Logout - Typically handled client-side by deleting tokens
# ---------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def organization_logout(request):
    """
    In a JWT-based system, logout is usually handled on the client side
    by simply deleting the stored tokens. You can also implement token
    blacklisting if needed.
    """
    return Response({'message': 'Logout successful (client-side token deletion required)'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def employee_login(request):
    """
    Authenticate an employee and return JWT tokens.
    """
    try:
        data = request.data
        # print("From Frontend =>", data)
        
        if not data.get('email') or not data.get('password'):
            return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Authenticate employee using the email and password.
        employee = authenticate(request, email=data.get('email'), password=data.get('password'))
        if employee is None:
            return Response({'error': 'Invalid email or password'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(employee)
        
        return Response({
            'message': 'Login successful',
            'employee': EmployeeSerializer(employee).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }, status=status.HTTP_200_OK)
    
    except Exception:
        logger.error(f"Employee login error: {traceback.format_exc()}")
        return Response({'error': 'Login failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_dashboard(request):
    try:
        user = request.user

        # Determine if the authenticated user is an EmployeeSignup or an Organization.
        if hasattr(user, 'organization'):
            # If user is an EmployeeSignup, then 'organization' is available and user has date_joined.
            org = user.organization
            employee_data = {
                'name': user.name,
                'email': user.email,
                'photo': request.build_absolute_uri(user.photo.url) if user.photo else None,
                'date_joined': user.date_joined,
            }
        else:
            # Otherwise, user is an Organization. We assume that the Organization object is acting as the user.
            org = user
            employee_data = {
                'name': user.name,
                'email': user.email,
                'photo': None,  # Organization doesn't have a date_joined or photo by design
                'date_joined': None,
            }

        total_queries = Query.objects.filter(owner=org).count()
        org_logo_url = request.build_absolute_uri(org.logo.url) if org.logo else None

        return Response({
            'message': f'Welcome {user.email} to Employee Dashboard',
            'employee': employee_data,
            'organization': {
                'name': org.name,
                'logo': org_logo_url,
            },
            'stats': {
                'total_queries': total_queries,
            }
        }, status=status.HTTP_200_OK)
        
    except Exception:
        logger.error(f"Employee dashboard error: {traceback.format_exc()}")
        return Response({'error': 'Failed to load dashboard. Please try again.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_monthly_attendance(request, year, month):
    # Get all employees for the organization
    employees = EmployeeSignup.objects.filter(organization=request.user)
    logger.info(f"Found {employees.count()} employees for the organization")
    for emp in employees:
        logger.info(f"Employee: {emp.unique_id} - {emp.name}")

    # Get the number of days in the month using local date
    _, days_in_month = monthrange(int(year), int(month))
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{days_in_month}"
    logger.info(f"Date range: {start_date} to {end_date}")

    # Query attendance records
    attendance_records = Attendance.objects.filter(
        employee__in=employees,
        date__range=[start_date, end_date]
    ).values('employee__unique_id', 'date', 'status')

    logger.info(f"Attendance records count: {attendance_records.count()}")
    print("Attendance records:", attendance_records)
    return Response(attendance_records)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def add_employee(request, company):
    """Add new employee with custom ID and optional RFID."""
    try:
        # Get the authenticated organization
        organization = request.user

        # Validate organization name matches
        if organization.name != company:
            return Response({
                'status': 'error',
                'message': 'Organization name mismatch'
            }, status=status.HTTP_403_FORBIDDEN)

        # Validate required fields
        required_fields = ['name', 'email', 'password', 'unique_id']
        for field in required_fields:
            if not request.data.get(field):
                return Response({
                    'status': 'error',
                    'message': f'{field.replace("_", " ").title()} is required'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Check if email already exists
        if EmployeeSignup.objects.filter(email=request.data['email']).exists():
            return Response({
                'status': 'error',
                'message': 'Email already registered'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if unique_id already exists
        if EmployeeSignup.objects.filter(unique_id=request.data['unique_id']).exists():
            return Response({
                'status': 'error',
                'message': 'Employee ID already exists'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate photo
        if not request.FILES.get('photo'):
            return Response({
                'status': 'error',
                'message': 'Employee photo is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        photo_error = validate_image(request.FILES['photo'])
        if photo_error:
            return Response({
                'status': 'error',
                'message': photo_error
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check RFID if provided
        rfid = request.data.get('rfid')
        if rfid and EmployeeSignup.objects.filter(rfid=rfid).exists():
            return Response({
                'status': 'error',
                'message': 'RFID card already assigned to another employee'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create employee
        employee = EmployeeSignup.objects.create(
            name=request.data['name'],
            email=request.data['email'],
            password=make_password(request.data['password']),
            unique_id=request.data['unique_id'],
            rfid=rfid,
            organization=organization,
            photo=request.FILES['photo'],
            is_active=True
        )

        return Response({
            'status': 'success',
            'message': 'Employee added successfully',
            'data': {
                'id': employee.id,
                'name': employee.name,
                'email': employee.email,
                'unique_id': employee.unique_id,
                'rfid': employee.rfid,
                'photo_url': request.build_absolute_uri(employee.photo.url)
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        print(f"⚠️ Error adding employee: {str(e)}")
        return Response({
            'status': 'error',
            'message': 'Failed to add employee',
            'debug_info': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_employee(request, employee_id):
    try:
        try:
            employee = EmployeeSignup.objects.get(id=employee_id, organization=request.user)
        except EmployeeSignup.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)
        
        employee.delete()
        return Response({'message': 'Employee removed successfully'}, status=status.HTTP_200_OK)
    except Exception:
        logger.error(f"Remove employee error: {traceback.format_exc()}")
        return Response({'error': 'Failed to remove employee. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_public_queries(request):
    try:
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 10)), 50)
        start = (page - 1) * page_size
        end = start + page_size
        
        queries = Query.objects.filter(visibility='public').order_by('-created_at')[start:end]
        total_queries = Query.objects.filter(visibility='public').count()
        
        return Response({
            'queries': ContactQuerySerializer(queries, many=True).data,
            'total': total_queries,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_queries + page_size - 1) // page_size
        }, status=status.HTTP_200_OK)
    except Exception:
        logger.error(f"Get public queries error: {traceback.format_exc()}")
        return Response({'error': 'Failed to fetch queries. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manage_employees(request):
    """
    Fetch a paginated list of employees belonging to the authenticated organization.
    This endpoint works with JWT since request.user is set when a valid JWT is provided.
    """
    try:
        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 10)), 50)
        start = (page - 1) * page_size
        end = start + page_size

        # Filter employees that belong to the organization (request.user)
        employees_qs = EmployeeSignup.objects.filter(organization=request.user).order_by('name')
        total_employees = employees_qs.count()
        employees = employees_qs[start:end]

        # Serialize the data
        serialized_employees = EmployeeSerializer(employees, many=True).data

        return Response({
            'employees': serialized_employees,
            'total': total_employees,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_employees + page_size - 1) // page_size
        }, status=status.HTTP_200_OK)
    except Exception:
        logger.error(f"Manage employees error: {traceback.format_exc()}")
        return Response({'error': 'Failed to fetch employees. Please try again.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_query(request):


    """
    Allow an authenticated organization to submit a query.
    """
    try:
        data = request.data
        query_content = data.get('query')
        if not query_content:
            return Response({'error': 'Query content is required'}, status=status.HTTP_400_BAD_REQUEST)
        if len(query_content) > 5000:
            return Response({'error': 'Query content must be under 5000 characters'}, status=status.HTTP_400_BAD_REQUEST)
        
        query = Query.objects.create(
            query=query_content,
            visibility=data.get('visibility', 'private'),
            owner=request.user
        )
        
        return Response({
            'message': 'Query submitted successfully',
            'query': ContactQuerySerializer(query).data
        }, status=status.HTTP_201_CREATED)
    except Exception:
        logger.error(f"Query submission error: {traceback.format_exc()}")
        return Response({'error': 'Query submission failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_server_time(request):
    """Return current server time in local timezone."""
    current_time = timezone.localtime()
    return Response({
        'datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
        'timestamp': int(current_time.timestamp()),
        'timezone': settings.TIME_ZONE
    })
    