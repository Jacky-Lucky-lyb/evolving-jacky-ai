# Evolving Self AI — Supabase database migration v0.1.1

1. Copy `0001_initial_schema.sql` into the public GitHub repository's `migrations/` directory and commit it.
2. In Supabase SQL Editor, paste the full contents of `0001_initial_schema.sql`, check the selected project, then Run **once** in an empty development database.
3. In a new SQL Editor query, run `0001_verify.sql`: expect 6 rows with `rls_enabled = true`.
4. Do not upload personal records yet. Client auth and Storage access policies are NOT included in this migration.

Important: This initial migration uses a restricted set of 9 node types and 12 relation types aligned with the current protocol. It is intended for a fresh database, not to upgrade an existing production schema. It does not implement automatic audit triggers, immutable audit trails or Git synchronization yet. Git and database changes are separate operations, and application code must handle syncing.

**Security note:** RLS protects rows for standard client roles, not elevated project administrators/service-role credentials. Never put `service_role` or database passwords in the repository or browser code.
