-- TASK-310 operator template. Run only as an authorized PostgreSQL
-- administrator after replacing every angle-bracket placeholder.
-- Never commit the substituted copy or its password.

CREATE ROLE <ROLE>
    LOGIN
    PASSWORD '<PASSWORD>'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

ALTER ROLE <ROLE> SET default_transaction_read_only = on;

GRANT CONNECT ON DATABASE <DATABASE> TO <ROLE>;
GRANT USAGE ON SCHEMA <SCHEMA> TO <ROLE>;

-- Exact data tables currently read by PostgresCrconRepository.
GRANT SELECT ON TABLE
    <SCHEMA>.map_history,
    <SCHEMA>.player_stats,
    <SCHEMA>.steam_id_64,
    <SCHEMA>.player_soldier,
    <SCHEMA>.player_names,
    <SCHEMA>.log_lines
TO <ROLE>;

-- Deliberately do not grant INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES,
-- TRIGGER, CREATE, ALTER, DROP, schema ownership or broad default privileges.
-- Review and grant each future table explicitly if application code starts to
-- read it. player_sessions and server_counts are schema-probed today but have
-- no application data query, so they receive no SELECT grant here.

-- Role and connection verification. Expected booleans are documented below.
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolinherit,
       rolreplication, rolbypassrls
FROM pg_catalog.pg_roles
WHERE rolname = '<ROLE>';

SELECT has_database_privilege('<ROLE>', '<DATABASE>', 'CONNECT') AS can_connect,
       has_schema_privilege('<ROLE>', '<SCHEMA>', 'USAGE') AS can_use_schema,
       has_schema_privilege('<ROLE>', '<SCHEMA>', 'CREATE') AS can_create_schema_objects;

SELECT table_name, privilege_type
FROM information_schema.role_table_grants
WHERE grantee = '<ROLE>'
  AND table_schema = '<SCHEMA>'
ORDER BY table_name, privilege_type;

SELECT table_name,
       has_table_privilege('<ROLE>', format('%I.%I', '<SCHEMA>', table_name), 'SELECT') AS can_select,
       has_table_privilege('<ROLE>', format('%I.%I', '<SCHEMA>', table_name), 'INSERT') AS can_insert,
       has_table_privilege('<ROLE>', format('%I.%I', '<SCHEMA>', table_name), 'UPDATE') AS can_update,
       has_table_privilege('<ROLE>', format('%I.%I', '<SCHEMA>', table_name), 'DELETE') AS can_delete,
       has_table_privilege('<ROLE>', format('%I.%I', '<SCHEMA>', table_name), 'TRUNCATE') AS can_truncate
FROM (VALUES
    ('map_history'),
    ('player_stats'),
    ('steam_id_64'),
    ('player_soldier'),
    ('player_names'),
    ('log_lines')
) AS required_tables(table_name)
ORDER BY table_name;

-- Expected: can_connect/can_use_schema/can_select=true;
-- can_create_schema_objects and every mutation privilege=false;
-- role capability flags above=false.

-- Structural evidence only: no player rows are returned.
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = '<SCHEMA>'
  AND table_name IN (
      'map_history', 'player_stats', 'player_sessions', 'steam_id_64',
      'player_soldier', 'player_names', 'log_lines'
  )
ORDER BY table_name, ordinal_position;

SELECT tablename, indexname, indexdef
FROM pg_catalog.pg_indexes
WHERE schemaname = '<SCHEMA>'
  AND tablename IN (
      'map_history', 'player_stats', 'player_sessions', 'steam_id_64',
      'player_soldier', 'player_names', 'log_lines'
  )
ORDER BY tablename, indexname;

SELECT tc.table_name, tc.constraint_name, tc.constraint_type,
       kcu.column_name, ccu.table_name AS referenced_table,
       ccu.column_name AS referenced_column
FROM information_schema.table_constraints AS tc
LEFT JOIN information_schema.key_column_usage AS kcu
  ON kcu.constraint_schema = tc.constraint_schema
 AND kcu.constraint_name = tc.constraint_name
LEFT JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_schema = tc.constraint_schema
 AND ccu.constraint_name = tc.constraint_name
WHERE tc.table_schema = '<SCHEMA>'
  AND tc.table_name IN (
      'map_history', 'player_stats', 'player_sessions', 'steam_id_64',
      'player_soldier', 'player_names', 'log_lines'
  )
ORDER BY tc.table_name, tc.constraint_name, kcu.ordinal_position;

-- Sanitized runtime values only. Expected semantics: 1=HLL, 2=HLLV.
-- game=2 is optional and need not exist.
SELECT game, count(*) AS map_count
FROM <SCHEMA>.map_history
GROUP BY game
ORDER BY game;
