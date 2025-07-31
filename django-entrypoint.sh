#!/bin/bash
set -e

echo "Starting Django application setup..."

# Function to wait for PostgreSQL to be ready
wait_for_postgres() {
    echo "Waiting for PostgreSQL at $LEARN_OPS_HOST:$LEARN_OPS_PORT..."
    while ! pg_isready -h "$LEARN_OPS_HOST" -p "$LEARN_OPS_PORT" -U "$LEARN_OPS_USER"; do
        sleep 1
    done
    echo "PostgreSQL is ready!"
}

# Wait for database to be ready
wait_for_postgres

# Generate Django superuser password if needed
if [ -n "$LEARN_OPS_SUPERUSER_PASSWORD" ] && [ -n "$LEARN_OPS_SUPERUSER_NAME" ]; then
    echo "Generating Django password hash..."
    if [ -f "./djangopass.py" ]; then
        export DJANGO_SETTINGS_MODULE="LearningPlatform.settings"
        DJANGO_GENERATED_PASSWORD=$(python3 ./djangopass.py "$LEARN_OPS_SUPERUSER_PASSWORD" 2>&1)
        # Ensure fixtures directory exists
        mkdir -p ./LearningAPI/fixtures
        
        # Create superuser fixture
        cat > ./LearningAPI/fixtures/superuser.json <<EOF
[
    {
        "model": "auth.user",
        "pk": null,
        "fields": {
            "password": "$DJANGO_GENERATED_PASSWORD",
            "last_login": null,
            "is_superuser": true,
            "username": "$LEARN_OPS_SUPERUSER_NAME",
            "first_name": "Admina",
            "last_name": "Straytor",
            "email": "me@me.com",
            "is_staff": true,
            "is_active": true,
            "date_joined": "2023-03-17T03:03:13.265Z",
            "groups": [
                2
            ],
            "user_permissions": []
        }
    }
]
EOF
        echo "Superuser fixture created."
    else
        echo "Warning: djangopass.py not found, skipping superuser creation."
    fi
fi

# Create social account fixture if client ID and secret are provided
if [ -n "$LEARN_OPS_CLIENT_ID" ] && [ -n "$LEARN_OPS_SECRET_KEY" ]; then
    echo "Creating social account configuration..."
    
    # Ensure fixtures directory exists
    mkdir -p ./LearningAPI/fixtures
    
    cat > ./LearningAPI/fixtures/socialaccount.json <<EOF
[
    {
       "model": "sites.site",
       "pk": 1,
       "fields": {
          "domain": "learningplatform.com",
          "name": "Learning Platform"
       }
    },
    {
        "model": "socialaccount.socialapp",
        "pk": 1,
        "fields": {
            "provider": "github",
            "name": "Github",
            "client_id": "$LEARN_OPS_CLIENT_ID",
            "secret": "$LEARN_OPS_SECRET_KEY",
            "key": "",
            "sites": [
                1
            ]
        }
    }
]
EOF
    echo "Social account fixture created."
fi

# Run migrations
echo "Running migrations..."
python3 manage.py migrate

# Load fixtures if they exist
if [ -f "./LearningAPI/fixtures/socialaccount.json" ]; then
    echo "Loading social account data..."
    python3 manage.py loaddata socialaccount || echo "Failed to load socialaccount data, continuing..."
    rm -f ./LearningAPI/fixtures/socialaccount.json
fi

if [ -f "./LearningAPI/fixtures/complete_backup.json" ]; then
    echo "Loading backup data..."
    python3 manage.py loaddata complete_backup || echo "Failed to load backup data, continuing..."
fi

if [ -f "./LearningAPI/fixtures/superuser.json" ]; then
    echo "Loading superuser data..."
    python3 manage.py loaddata superuser || echo "Failed to load superuser data, continuing..."
fi

# Collect static files
echo "Collecting static files..."
python3 manage.py collectstatic --noinput || echo "Failed to collect static files, continuing..."

# ... existing script content ...

echo "Django setup complete!"

# Start the Django development server
echo "Starting Django development server..."
exec python manage.py runserver 0.0.0.0:8000