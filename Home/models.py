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
from datetime import date
from djongo import models  # Djongo’s model imports
from django.utils import timezone
from django.utils.text import slugify

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
class EmployeeSignup(AbstractBaseUser, PermissionsMixin):
    unique_id = models.CharField(
        max_length=12, 
        unique=True, 
        
        blank=False  # Make it required
    )
    rfid = models.CharField(max_length=50, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)
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
        """Helper method to find employee by RFID"""
        try:
            return cls.objects.filter(
                rfid=card_uid,
                is_active=True
            ).first()
        except Exception as e:
            print(f"RFID lookup error: {str(e)}")
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

# Attendance Model
class Attendance(models.Model):
    employee = models.OneToOneField('EmployeeSignup', primary_key=True, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    timestamp = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=1, choices=[
        ('P', 'Present'),
        ('A', 'Absent'),
        ('L', 'Leave'),
    ], default='A')

    class Meta:
        indexes = [
            models.Index(fields=['employee', 'date']),
        ]

    @classmethod
    def mark_attendance(cls, employee, status, timestamp=None):
        """
        Marks attendance for an employee.
        This version will create or update one record per employee.
        """
        attendance, created = cls.objects.get_or_create(
            employee=employee,  # OneToOne ensures one record per employee.
            defaults={'status': status, 'timestamp': timestamp or timezone.now()}
        )
        if not created:
            attendance.status = status
            attendance.timestamp = timestamp or timezone.now()
            attendance.date = date.today()
            attendance.save()
        return attendance

    def __str__(self):
        try:
            name = self.employee.name
        except Exception:
            from Home.models import EmployeeSignup
            try:
                emp = EmployeeSignup.objects.get(pk=self.employee_id)
                name = emp.name
            except Exception:
                name = str(self.employee_id)
        return f"{name} - {self.date} - {self.get_status_display()}"