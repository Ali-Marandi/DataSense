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

-- Action Gate rollout, permit fencing, and Trust Exchange registry are metadata-only.
CREATE TABLE action_gate_rollout_states (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  scope text NOT NULL CHECK (scope ~ '^[a-z][a-z0-9_.-]{2,127}$'),
  mode text NOT NULL CHECK (mode IN ('shadow','limited_enforce','enforce','rollback_active','manual_kill')),
  execution_mode text NOT NULL CHECK (execution_mode IN ('observe_only','allow_guarded','suppress_external')),
  active_policy_digest char(71) NOT NULL CHECK (active_policy_digest ~ '^sha256:[a-f0-9]{64}$'),
  last_known_good_policy_digest char(71) NOT NULL CHECK (last_known_good_policy_digest ~ '^sha256:[a-f0-9]{64}$'),
  version bigint NOT NULL DEFAULT 0 CHECK (version >= 0),
  gate_epoch bigint NOT NULL DEFAULT 0 CHECK (gate_epoch >= 0),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, scope)
);

CREATE TABLE action_gate_rollback_events (
  rollback_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id),
  scope text NOT NULL,
  trigger_type text NOT NULL CHECK (trigger_type ~ '^[a-z][a-z0-9_.-]{2,127}$'),
  reason_code text NOT NULL CHECK (reason_code ~ '^[a-z][a-z0-9_.-]{2,127}$'),
  trigger_evidence_digest char(71) NOT NULL CHECK (trigger_evidence_digest ~ '^sha256:[a-f0-9]{64}$'),
  transition_status text NOT NULL CHECK (transition_status IN ('pending','committed','suppressed')),
  previous_state jsonb NOT NULL DEFAULT '{}'::jsonb,
  target_state jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  UNIQUE (organization_id, scope, trigger_evidence_digest)
);

CREATE TABLE action_gate_permits (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  execution_key text NOT NULL CHECK (execution_key ~ '^[a-zA-Z0-9_.:-]{8,128}$'),
  scope text NOT NULL,
  receipt_digest char(71) NOT NULL CHECK (receipt_digest ~ '^sha256:[a-f0-9]{64}$'),
  gate_epoch bigint NOT NULL CHECK (gate_epoch >= 0),
  state text NOT NULL CHECK (state IN ('reserved','committed','suppressed','expired')),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  committed_at timestamptz,
  PRIMARY KEY (organization_id, execution_key)
);
CREATE INDEX action_gate_permits_expiry_idx ON action_gate_permits (organization_id, expires_at)
  WHERE state = 'reserved';

CREATE TABLE trust_exchange_relationships (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  relationship_id text NOT NULL CHECK (relationship_id ~ '^[a-zA-Z0-9_.:-]{8,128}$'),
  issuer text NOT NULL CHECK (issuer ~ '^urn:datasense:issuer:[a-zA-Z0-9_.:-]{3,128}$'),
  receiver_organization_id uuid NOT NULL REFERENCES organizations(id),
  environment text NOT NULL CHECK (environment IN ('staging','production')),
  allowed_action_types jsonb NOT NULL,
  max_receipt_lifetime_seconds integer NOT NULL CHECK (max_receipt_lifetime_seconds BETWEEN 60 AND 900),
  status text NOT NULL CHECK (status IN ('pending','active','suspended','revoked')),
  version bigint NOT NULL DEFAULT 0 CHECK (version >= 0),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, relationship_id)
);

CREATE TABLE trust_exchange_signing_keys (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  issuer text NOT NULL,
  key_id text NOT NULL CHECK (key_id ~ '^[a-zA-Z0-9_.:-]{3,128}$'),
  algorithm text NOT NULL CHECK (algorithm = 'EdDSA'),
  key_type text NOT NULL CHECK (key_type = 'OKP'),
  curve text NOT NULL CHECK (curve = 'Ed25519'),
  public_key_base64url text NOT NULL CHECK (public_key_base64url ~ '^[A-Za-z0-9_-]{43}$'),
  status text NOT NULL CHECK (status IN ('active','retiring','revoked')),
  not_before timestamptz NOT NULL,
  not_after timestamptz NOT NULL,
  revoked_at timestamptz,
  revocation_reason_code text,
  version bigint NOT NULL DEFAULT 0 CHECK (version >= 0),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, issuer, key_id),
  CHECK (not_after > not_before)
);

ALTER TABLE action_gate_rollout_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_gate_rollback_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_gate_permits ENABLE ROW LEVEL SECURITY;
ALTER TABLE trust_exchange_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE trust_exchange_signing_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY action_gate_rollout_isolation ON action_gate_rollout_states
  USING (organization_id::text = current_setting('app.organization_id', true));
CREATE POLICY action_gate_rollback_isolation ON action_gate_rollback_events
  USING (organization_id::text = current_setting('app.organization_id', true));
CREATE POLICY action_gate_permit_isolation ON action_gate_permits
  USING (organization_id::text = current_setting('app.organization_id', true));
CREATE POLICY trust_exchange_relationship_isolation ON trust_exchange_relationships
  USING (organization_id::text = current_setting('app.organization_id', true));
CREATE POLICY trust_exchange_key_isolation ON trust_exchange_signing_keys
  USING (organization_id::text = current_setting('app.organization_id', true));
