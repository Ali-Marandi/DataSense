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
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','sent','dead','suppressed')),
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  next_attempt_at timestamptz NOT NULL DEFAULT now(),
  lease_expires_at timestamptz,
  lease_owner text,
  last_error_code text,
  sent_at timestamptz,
  dead_at timestamptz,
  suppressed_at timestamptz,
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

-- Activation governance state is intentionally metadata-only and fully tenant-scoped.
CREATE TABLE activation_circuit_states (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  scope text NOT NULL CHECK (scope ~ '^[a-z][a-z0-9_.-]{2,127}$'),
  state text NOT NULL CHECK (state IN ('closed','open','half_open','manual_kill')),
  version bigint NOT NULL DEFAULT 0 CHECK (version >= 0),
  reason_code text NOT NULL CHECK (reason_code ~ '^[a-z][a-z0-9_.-]{2,127}$'),
  opened_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, scope)
);

CREATE TABLE activation_circuit_approvals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id),
  scope text NOT NULL,
  transition text NOT NULL CHECK (transition IN ('open_to_half_open','half_open_to_closed')),
  approved_by text NOT NULL CHECK (approved_by ~ '^[a-zA-Z0-9_.:@/-]{3,128}$'),
  approval_reference text NOT NULL CHECK (approval_reference ~ '^[a-zA-Z0-9_.:@/-]{3,128}$'),
  approved_at timestamptz NOT NULL,
  UNIQUE (organization_id, scope, transition, approval_reference)
);

CREATE TABLE activation_half_open_probes (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  scope text NOT NULL,
  window_started_at timestamptz NOT NULL,
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0 AND attempts <= 5),
  PRIMARY KEY (organization_id, scope, window_started_at)
);

CREATE TABLE activation_delivery_consents (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  recipient_ref_hash char(64) NOT NULL CHECK (recipient_ref_hash ~ '^[a-f0-9]{64}$'),
  channel text NOT NULL CHECK (channel IN ('external')),
  granted boolean NOT NULL,
  version bigint NOT NULL DEFAULT 0 CHECK (version >= 0),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, recipient_ref_hash, channel)
);

CREATE TABLE activation_trigger_executions (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  execution_key char(64) NOT NULL CHECK (execution_key ~ '^[a-f0-9]{64}$'),
  state text NOT NULL CHECK (state IN ('started','effect_recorded','suppressed','failed')),
  provider_idempotency_key char(64) NOT NULL CHECK (provider_idempotency_key ~ '^[a-f0-9]{64}$'),
  reason_code text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, execution_key)
);

CREATE TABLE activation_kill_switches (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  scope text NOT NULL CHECK (scope ~ '^[a-z][a-z0-9_.-]{2,127}$'),
  enabled boolean NOT NULL DEFAULT false,
  version bigint NOT NULL DEFAULT 0 CHECK (version >= 0),
  updated_by text NOT NULL CHECK (updated_by ~ '^[a-zA-Z0-9_.:@/-]{3,128}$'),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, scope)
);

ALTER TABLE activation_circuit_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE activation_circuit_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE activation_half_open_probes ENABLE ROW LEVEL SECURITY;
ALTER TABLE activation_delivery_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE activation_trigger_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE activation_kill_switches ENABLE ROW LEVEL SECURITY;
CREATE POLICY activation_circuit_state_isolation ON activation_circuit_states
  USING (organization_id::text = current_setting('app.organization_id', true));
CREATE POLICY activation_circuit_approval_isolation ON activation_circuit_approvals
  USING (organization_id::text = current_setting('app.organization_id', true));
CREATE POLICY activation_half_open_probe_isolation ON activation_half_open_probes
  USING (organization_id::text = current_setting('app.organization_id', true));
CREATE POLICY activation_delivery_consent_isolation ON activation_delivery_consents
  USING (organization_id::text = current_setting('app.organization_id', true));
CREATE POLICY activation_trigger_execution_isolation ON activation_trigger_executions
  USING (organization_id::text = current_setting('app.organization_id', true));
CREATE POLICY activation_kill_switch_isolation ON activation_kill_switches
  USING (organization_id::text = current_setting('app.organization_id', true));
