#!/bin/bash
set -e

# PostgreSQL initialization script
# This replicates the database setup from the bash script

echo "Setting up custom database and user..."

# Create the application database and user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Terminate any existing connections to the database
    SELECT pg_terminate_backend(pid) 
    FROM pg_stat_activity 
    WHERE datname = '$LEARN_OPS_DB' AND pid <> pg_backend_pid();

    -- Drop database if it exists
    DROP DATABASE IF EXISTS $LEARN_OPS_DB;
    
    -- Create database
    CREATE DATABASE $LEARN_OPS_DB;
    
    -- Create user if it doesn't exist
    DO \$\$
    BEGIN
        CREATE USER $LEARN_OPS_USER WITH PASSWORD '$LEARN_OPS_PASSWORD';
        EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'User already exists';
    END
    \$\$;
    
    -- Set user properties (replicating the bash script settings)
    ALTER ROLE $LEARN_OPS_USER SET client_encoding TO 'utf8';
    ALTER ROLE $LEARN_OPS_USER SET default_transaction_isolation TO 'read committed';
    ALTER ROLE $LEARN_OPS_USER SET timezone TO 'UTC';
    
    -- Grant privileges
    GRANT ALL PRIVILEGES ON DATABASE $LEARN_OPS_DB TO $LEARN_OPS_USER;
EOSQL

echo "Database setup complete!"