#! /bin/bash
set +o histexpand
set -eu

# Takes parameters we pass in and sets them as local variables
for i in "$@"; do
    case $i in
    -d=* | --database=*) DATABASE="${i#*=}" ;;
    -u=* | --user=*) DB_USER="${i#*=}" ;;
    -p=* | --password=*) PASSWORD="${i#*=}" ;;
    -c=* | --clientid=*) CLIENTID="${i#*=}" ;;
    -s=* | --secretkey=*) SECRETKEY="${i#*=}" ;;
    -j=* | --superpass=*) SUPERPASS="${i#*=}" ;;
    -r=* | --superuser=*) SUPERUSER="${i#*=}" ;;
    *) ;; # unkown option ;;
    esac
done

# Update homebrew - the package manager for Mac
# TODO: uncomment this
# brew update

# Check to see if pyenv is already installed, if so skip installation of pyenv
# &> the & is wildcard, meaning all output in this case, 1 is standard output, 2 is error output
if command -v pyenv &>/dev/null; then
    echo "pyenv is installed."
else
    # Install pyenv
    brew install pyenv

    # Add necessary config to shell profile (.zshrc)
    echo 'export PATH="$HOME/.pyenv/bin:$PATH"
    eval "$(pyenv init --path)"
    eval "$(pyenv virtualenv-init -)"' >>$HOME/.zshrc

    # Update path of current subshell execution
    export PATH="$HOME/.pyenv/bin:$PATH"
    eval "$(pyenv init --path)"
    eval "$(pyenv virtualenv-init -)"
fi

# Check if Python 3.9.1 is installed
if pyenv versions --bare | grep -q '^3.9.1$'; then
    echo "Python 3.9.1 is already installed."
else
    echo "Python 3.9.1 is not installed. Installing now..."
    pyenv install 3.9.1
fi

# Get the global Python version set in pyenv
global_version=$(pyenv global)

# Check that global version of python is 3.9.1
if [[ $global_version == '3.9.1' ]]; then
    echo "Python 3.9.1 is the global version."
else
    echo "Python 3.9.1 is not the global version. The global version is $global_version."
    echo "Setting global version of python to 3.9.1"
    pyenv global 3.9.1
fi

# Check if PostgreSQL is installed
if ! command -v psql &>/dev/null; then
    echo "PostgreSQL is not installed"
    brew install postgresql
    brew services start postgresql
fi

# Drop database before it's (re)created

psql -c "DROP DATABASE IF EXISTS $DATABASE WITH (FORCE);"
psql -c "CREATE DATABASE $DATABASE;"
# Create user if needed
psql -tAc "SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER'" | grep -q 1 || \
psql -c "CREATE USER $DB_USER WITH PASSWORD '$PASSWORD';"

# Set user options
psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"

# Grant privileges on DB
psql -c "GRANT ALL PRIVILEGES ON DATABASE $DATABASE TO $DB_USER;"

# Schema ownership + rights
psql -d "$DATABASE" -c "ALTER SCHEMA public OWNER TO $DB_USER;"
psql -d "$DATABASE" -c "GRANT USAGE, CREATE ON SCHEMA public TO $DB_USER;"





# Check if Pipenv is installed
if ! command -v pipenv &>/dev/null; then
    echo "Pipenv not found. Installing Pipenv..."
    pip3 install pipenv
    echo "Pipenv installation complete."
else
    echo "Pipenv is already installed."
fi

# Use venv to create the virtual env directory
# Running venv will create directory called 'venv' in project directory
# Get the path of the virtual environment
# Create environment variable
export VIRTUAL_ENV="$(pwd)/venv"
echo "VIRTUAL_ENV=$VIRTUAL_ENV" >.env
python3 -m venv $VIRTUAL_ENV

# Activate the virtual environment
source $VIRTUAL_ENV/bin/activate

# Wheel is a dependency needed for several packages for our API app
pip3 install wheel

# Install dependencies from requirements.txt file
pip3 install -r requirements.txt

# This is where we left off on Thursday
# TODO: Don't need any of this for mac
PSFILEPATH=$(psql -c 'SHOW hba_file;' | sed -n '3p' | xargs)

# Replace `scram-sha-256` with `trust` in the pg_hba file to enable peer authentication
sudo sed -i -e 's/scram-sha-256/trust/g' $PSFILEPATH

# Restart postgres service
brew services restart postgresql@16

echo "Generating Django password"
export DJANGO_SETTINGS_MODULE="LearningPlatform.settings"
echo "$SUPERPASS"

# Takes plain text password and uses the `djangopass` utility module to encrypt it
DJANGO_GENERATED_PASSWORD=$(python3 ./djangopass.py "$SUPERPASS" >&1)

# Use the `tee` command to create a superuser.json fixture with embedded username and password for admin
sudo tee ./LearningAPI/fixtures/superuser.json <<EOF
[
    {
        "model": "auth.user",
        "pk": null,
        "fields": {
            "password": "$DJANGO_GENERATED_PASSWORD",
            "last_login": null,
            "is_superuser": true,
            "username": "$SUPERUSER",
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

# Use echo command to create fixture for the Github OAuth credentials used during authentication
echo '[
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
            "client_id": "'"$CLIENTID"'",
            "secret": "'"$SECRETKEY"'",
            "key": "",
            "sites": [
                1
            ]
        }
    }
  ]
' >./LearningAPI/fixtures/socialaccount.json

# Run Django migrations
python3 manage.py migrate

# Seed data from backup, OAuth and superuser
python3 manage.py loaddata socialaccount
python3 manage.py loaddata complete_backup
python3 manage.py loaddata superuser

# Delete fixtures with sensitive information to prevent inadvertant inclusion in the repo
rm ./LearningAPI/fixtures/socialaccount.json
rm ./LearningAPI/fixtures/superuser.json