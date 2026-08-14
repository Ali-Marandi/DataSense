CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE organizations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$'),
  display_name text NOT NULL,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','deleted')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE identities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issuer text NOT NULL,
  external_subject text NOT NULL,
  email text,
  display_name text,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_authenticated_at timestamptz,
  UNIQUE (issuer, external_subject)
);

CREATE TABLE memberships (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id),
  identity_id uuid NOT NULL REFERENCES identities(id),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','revoked')),
  created_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz,
  UNIQUE (organization_id, identity_id)
);

CREATE TABLE roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid REFERENCES organizations(id),
  name text NOT NULL,
  is_system_role boolean NOT NULL DEFAULT false,
  UNIQUE NULLS NOT DISTINCT (organization_id, name)
);

CREATE TABLE permissions (
  code text PRIMARY KEY,
  description text NOT NULL
);

CREATE TABLE role_permissions (
  role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_code text NOT NULL REFERENCES permissions(code),
  PRIMARY KEY (role_id, permission_code)
);

CREATE TABLE membership_roles (
  membership_id uuid NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
  role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  granted_by_membership_id uuid REFERENCES memberships(id),
  granted_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (membership_id, role_id)
);

CREATE TABLE saml_connections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL UNIQUE REFERENCES organizations(id),
  idp_entity_id text NOT NULL,
  idp_sso_url text NOT NULL CHECK (idp_sso_url ~ '^https://'),
  idp_x509_cert_pem text NOT NULL,
  sp_entity_id text NOT NULL UNIQUE,
  acs_url text NOT NULL CHECK (acs_url ~ '^https://'),
  attribute_mapping jsonb NOT NULL DEFAULT '{}'::jsonb,
  require_encrypted_assertion boolean NOT NULL DEFAULT true,
  enabled boolean NOT NULL DEFAULT true,
  metadata_verified_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid REFERENCES organizations(id),
  actor_identity_id uuid REFERENCES identities(id),
  action text NOT NULL,
  outcome text NOT NULL CHECK (outcome IN ('allowed','denied','success','failure')),
  resource_type text,
  resource_id_hash text,
  correlation_id uuid NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  details jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX audit_events_org_time_idx ON audit_events (organization_id, occurred_at DESC);
CREATE INDEX audit_events_correlation_idx ON audit_events (correlation_id);

-- Outbox payloads must contain metadata-only, versioned event bodies. They are never Prometheus labels.
CREATE TABLE outbox_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id),
  event_type text NOT NULL CHECK (event_type ~ '^[a-z][a-z0-9_.-]{2,127}$'),
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  idempotency_key text NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','sent','dead')),
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  next_attempt_at timestamptz NOT NULL DEFAULT now(),
  lease_expires_at timestamptz,
  lease_owner text,
  last_error_code text,
  sent_at timestamptz,
  dead_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, idempotency_key)
);
CREATE INDEX outbox_claim_idx ON outbox_events (status, next_attempt_at, created_at)
  WHERE status = 'pending';
CREATE INDEX outbox_lease_idx ON outbox_events (lease_expires_at)
  WHERE status = 'processing';
CREATE INDEX outbox_dead_idx ON outbox_events (organization_id, dead_at DESC)
  WHERE status = 'dead';

-- Metadata-only Quality Gate evidence from an authenticated client or scheduler.
CREATE TABLE quality_gate_observations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id),
  execution_id text NOT NULL,
  contract_fingerprint char(64) NOT NULL,
  policy_tier text NOT NULL CHECK (policy_tier IN ('sandbox','standard','tier_1','restricted')),
  decision text NOT NULL CHECK (decision IN ('approved','blocked','not_configured')),
  score numeric(5,1),
  critical_failures integer NOT NULL DEFAULT 0 CHECK (critical_failures >= 0),
  high_failures integer NOT NULL DEFAULT 0 CHECK (high_failures >= 0),
  rule_errors integer NOT NULL DEFAULT 0 CHECK (rule_errors >= 0),
  rows_examined bigint NOT NULL DEFAULT 0 CHECK (rows_examined >= 0),
  actor_subject text NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, execution_id)
);
CREATE INDEX quality_gate_observations_org_time_idx
  ON quality_gate_observations (organization_id, recorded_at DESC);

-- Application role must only have DML rights; migrations run under a separate owner role.
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE saml_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE quality_gate_observations ENABLE ROW LEVEL SECURITY;
-- The repository sets: SET LOCAL app.organization_id = '<UUID>' for every scoped transaction.
CREATE POLICY organization_isolation ON organizations
  USING (id::text = current_setting('app.organization_id', true));
CREATE POLICY membership_isolation ON memberships
  USING (organization_id::text = current_setting('app.organization_id', true));
CREATE POLICY saml_connection_isolation ON saml_connections
  USING (organization_id::text = current_setting('app.organization_id', true));
CREATE POLICY outbox_organization_isolation ON outbox_events
  USING (organization_id::text = current_setting('app.organization_id', true));
CREATE POLICY quality_gate_observation_isolation ON quality_gate_observations
  USING (organization_id::text = current_setting('app.organization_id', true));
