import uuid
from django.db import models
from django.core.validators import EmailValidator
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
    Group,
    Permission,
    AbstractUser,
)
from datetime import date, datetime
from djongo import models  # Djongo’s model imports
from django.utils import timezone
from django.utils.text import slugify
from bson import ObjectId  # ensure you have pymongo installed

# Function to generate a unique 12-character ID
def generate_uuid():
    return uuid.uuid4().hex[:12]

# Organization Manager
class OrganizationManager(BaseUserManager):
    def create_user(self, name, email, password=None):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        org = self.model(name=name, email=email)
        if password:
            org.set_password(password)
        org.save(using=self._db)
        return org

    def create_superuser(self, name, email, password):
        org = self.create_user(name, email, password)
        org.is_superuser = True
        org.is_staff = True
        org.save(using=self._db)
        return org

# Organization Model
class Organization(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    password = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='logos/', null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    groups = models.ManyToManyField(Group, related_name="organization_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="organization_permissions", blank=True)

    objects = OrganizationManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
       
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.name

# Employee Manager
class EmployeeSignupManager(BaseUserManager):
    def create_user(self, email, name, unique_id, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        if not unique_id:
            raise ValueError("The Employee ID field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, name=name, unique_id=unique_id, **extra_fields)
        
        if password:
            user.set_password(password)
            
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, unique_id, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, name, unique_id, password, **extra_fields)

# Employee Model
class EmployeeSignup(models.Model):
    unique_id = models.CharField(
        max_length=100, 
        unique=True, 
        blank=False  # Make it required
    )
    rfid = models.CharField(max_length=50, null=True, blank=True, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    date_joined = models.DateTimeField(auto_now_add=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='employees')
    photo = models.ImageField(upload_to='employees_photos/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    groups = models.ManyToManyField(Group, related_name="employee_signup_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="employee_signup_permissions", blank=True)

    objects = EmployeeSignupManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'unique_id']  # Include unique_id as required

    @classmethod
    def find_by_rfid(cls, card_uid):
        """
        Lookup an employee by their RFID (case insensitive).
        Returns the employee if found; otherwise, returns None.
        """
        try:
            return cls.objects.get(rfid__iexact=card_uid)
        except cls.DoesNotExist:
            return None

    def __str__(self):
        return f"{self.unique_id} - {self.name}"


# Query Model
class Query(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
        ('in_progress', 'In Progress'),
    ]

    subject = models.CharField(max_length=200)
    description = models.TextField()
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Queries"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} - {self.organization}"

# RFID Card Model
class RFIDCard(models.Model):
    card_uid = models.CharField(max_length=50, unique=True)
    scanned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Card UID: {self.card_uid} - Scanned at {self.scanned_at}"


def today_date():
    """Return today's date."""
    return timezone.now().date()


# Attendance Model
class Attendance(models.Model):
    """
    Model for recording daily attendance.
    Records employee check-in details along with employee unique id and organization name.
    """
    _id = models.ObjectIdField(primary_key=True, default=ObjectId, editable=False)
    employee = models.ForeignKey(
        'EmployeeSignup',
        on_delete=models.CASCADE,
        related_name="attendances"
    )
    # New fields to store employee unique id and organization name
    employee_unique_id = models.CharField(max_length=100, blank=True, null=True)
    organization_name = models.CharField(max_length=255, blank=True, null=True)

    date = models.DateField(default=today_date)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=1,
        choices=[
            ('P', 'Present'),
            ('A', 'Absent'),
            ('L', 'Leave'),
            ('H', 'Half Day'),
        ],
        default='A'
    )

    class Meta:
        unique_together = ('employee', 'date')
        indexes = [
            models.Index(fields=['employee', 'date']),
        ]

    @classmethod
    def mark_attendance(cls, employee, status='P', check_time=None):
        """
        Creates or updates today's attendance record for the employee.
        Records the employee's unique id, organization name, check_in time, and status.
        """
        if not check_time:
            check_time = timezone.now()
        today = check_time.date()

        # Attempt to retrieve an existing attendance record or create a new one
        attendance, created = cls.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                'check_in': check_time,
                'status': status,
                'employee_unique_id': employee.unique_id,  # Make sure EmployeeSignup has unique_id
                'organization_name': employee.organization.name if hasattr(employee, 'organization') else ""
            }
        )
        # If record already exists, update check_out and status
        if not created:
            attendance.check_out = check_time
            attendance.status = status
            attendance.save()
        return attendance, created

    def __str__(self):
        return f"{self.employee.name} - {self.date} - {self.get_status_display()}"


# Attendance Record Model
class AttendanceRecord(models.Model):
    """
    Model for recording daily attendance with proper MongoDB integration.
    """
    employee = models.ForeignKey(
        'EmployeeSignup',
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    date = models.DateField(default=today_date)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=1,
        choices=[
            ('P', 'Present'),
            ('A', 'Absent'),
            ('L', 'Leave'),
            ('H', 'Half Day'),
        ],
        default='A'
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date', 'status'])
        ]
        unique_together = ['employee', 'date']

    @classmethod
    def record_attendance(cls, employee, status='P', check_time=None):
        """
        Records attendance for an employee.
        """
        if not check_time:
            check_time = timezone.now()
        today = check_time.date()
        attendance, created = cls.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                'status': status,
                'check_in': check_time
            }
        )
        if not created:
            if status == 'P':
                attendance.check_out = check_time
            attendance.status = status
            attendance.save()
        return attendance

    @classmethod
    def get_daily_attendance(cls, target_date=None):
        """
        Get attendance records for a specific date.
        """
        if not target_date:
            target_date = today_date()
        records = cls.objects.filter(date=target_date).select_related('employee').order_by('employee__name')
        attendance_list = []
        for record in records:
            attendance_list.append({
                'name': record.employee.name,
                'employee_id': record.employee.unique_id,
                'status': record.get_status_display(),
                'check_in': record.check_in.strftime('%I:%M %p') if record.check_in else 'N/A',
                'check_out': record.check_out.strftime('%I:%M %p') if record.check_out else 'N/A'
            })
        return attendance_list

    @classmethod
    def get_monthly_report(cls, year, month, employee=None):
        """
        Generate monthly attendance report.
        """
        query = {
            'date__year': year,
            'date__month': month
        }
        if employee:
            query['employee'] = employee
        records = cls.objects.filter(**query).select_related('employee')
        report = {}
        for record in records:
            emp_id = record.employee.unique_id
            if emp_id not in report:
                report[emp_id] = {
                    'name': record.employee.name,
                    'present': 0,
                    'absent': 0,
                    'leave': 0,
                    'half_day': 0
                }
            if record.status == 'P':
                report[emp_id]['present'] += 1
            elif record.status == 'A':
                report[emp_id]['absent'] += 1
            elif record.status == 'L':
                report[emp_id]['leave'] += 1
            elif record.status == 'H':
                report[emp_id]['half_day'] += 1
        return report

    def __str__(self):
        return f"{self.employee.name} - {self.date} - {self.get_status_display()}"
