import os

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Home.settings")  # Replace 'Backend' with your actual project name

# Start the Django development server
os.system("python manage.py runserver 0.0.0.0:8000")
 