#!/bin/bash
set -e

echo "Setting up custom database and user..."

# First, create the user and database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create user if it doesn't exist
    DO \$\$
    BEGIN
        CREATE USER $LEARN_OPS_USER WITH PASSWORD '$LEARN_OPS_PASSWORD';
        EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'User already exists';
    END
    \$\$;
    
    -- Terminate any existing connections to the database
    SELECT pg_terminate_backend(pid) 
    FROM pg_stat_activity 
    WHERE datname = '$LEARN_OPS_DB' AND pid <> pg_backend_pid();

    -- Drop database if it exists
    DROP DATABASE IF EXISTS $LEARN_OPS_DB;
    
    -- Create database with the user as owner
    CREATE DATABASE $LEARN_OPS_DB WITH OWNER = $LEARN_OPS_USER;
    
    -- Set user properties
    ALTER ROLE $LEARN_OPS_USER SET client_encoding TO 'utf8';
    ALTER ROLE $LEARN_OPS_USER SET default_transaction_isolation TO 'read committed';
    ALTER ROLE $LEARN_OPS_USER SET timezone TO 'UTC';
EOSQL

# Now connect to the new database and set up schema permissions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$LEARN_OPS_DB" <<-EOSQL
    -- Transfer ownership of public schema to the user
    ALTER SCHEMA public OWNER TO $LEARN_OPS_USER;
    
    -- Grant all privileges on the public schema
    GRANT ALL ON SCHEMA public TO $LEARN_OPS_USER;
    
    -- Grant privileges on all current and future tables
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $LEARN_OPS_USER;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $LEARN_OPS_USER;
    
    -- Set default privileges for future objects
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $LEARN_OPS_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $LEARN_OPS_USER;
EOSQL

echo "Database setup complete!"