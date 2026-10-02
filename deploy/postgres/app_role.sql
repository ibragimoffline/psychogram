-- Least-privilege role for the Psychogram API process.
--
-- Run with psql as the database owner after every `alembic upgrade head`:
--   psql -d psychogram -v app_password='...' -f deploy/postgres/app_role.sql
-- Migrations keep running as the owner; the API connects as psychogram_app.
--
-- The application only appends to results, traces, audit events and other history
-- tables. Withholding UPDATE and DELETE there makes that immutability hold for direct
-- SQL through the application credentials too, not only through the ORM hook.

\set ON_ERROR_STOP on

\if :{?app_password}
\else
  \echo 'Set the password: psql -v app_password=... -f deploy/postgres/app_role.sql'
  \quit
\endif

SELECT NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'psychogram_app') AS create_app_role \gset
\if :create_app_role
  CREATE ROLE psychogram_app LOGIN;
\endif
ALTER ROLE psychogram_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_password';

GRANT CONNECT ON DATABASE :"DBNAME" TO psychogram_app;
GRANT USAGE ON SCHEMA public TO psychogram_app;
REVOKE CREATE ON SCHEMA public FROM psychogram_app;

-- Start from nothing so re-running the script also removes grants that were dropped here.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM psychogram_app;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO psychogram_app;
REVOKE INSERT ON alembic_version FROM psychogram_app;

-- Tables whose rows the services update in place (status, lock version, publish metadata,
-- encrypted PII envelope). Keep this list in step with the code when adding an update path.
GRANT UPDATE ON
  researches,
  responses,
  response_revisions,
  calculation_runs,
  import_jobs,
  methodology_versions,
  participant_pii
TO psychogram_app;

-- The only delete path: removing a participant's encrypted PII (blocked by legal hold).
GRANT DELETE ON participant_pii TO psychogram_app;
