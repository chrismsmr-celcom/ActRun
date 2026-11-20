-- Organization invitations and per-agent credentials.
-- Runtime workspace partitioning is intentionally a separate migration: do not
-- enable multi-organization API traffic until every runtime query is tenant-scoped.
BEGIN;

CREATE TABLE IF NOT EXISTS public.cohort_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.cohort_organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'member', 'viewer')),
    token_hash TEXT NOT NULL UNIQUE,
    invited_by UUID NOT NULL REFERENCES auth.users(id),
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    accepted_by UUID REFERENCES auth.users(id),
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (accepted_at IS NULL OR revoked_at IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_cohort_invitations_org_email
    ON public.cohort_invitations (organization_id, lower(email))
    WHERE accepted_at IS NULL AND revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_cohort_invitations_expiry
    ON public.cohort_invitations (expires_at)
    WHERE accepted_at IS NULL AND revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS public.cohort_agent_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.cohort_organizations(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL CHECK (length(agent_id) BETWEEN 1 AND 128),
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 120),
    token_hash TEXT NOT NULL UNIQUE,
    scopes TEXT[] NOT NULL DEFAULT ARRAY['workspace:read', 'workspace:write', 'leases:read', 'leases:write'],
    created_by UUID NOT NULL REFERENCES auth.users(id),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, agent_id, id)
);

CREATE INDEX IF NOT EXISTS idx_cohort_agent_credentials_org_agent
    ON public.cohort_agent_credentials (organization_id, agent_id)
    WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_cohort_agent_credentials_active
    ON public.cohort_agent_credentials (token_hash)
    WHERE revoked_at IS NULL;

ALTER TABLE public.cohort_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cohort_agent_credentials ENABLE ROW LEVEL SECURITY;

-- Invitations and agent secrets are never directly readable by browser clients.
-- Management and redemption must go through authenticated server endpoints.
REVOKE ALL ON public.cohort_invitations FROM anon, authenticated;
REVOKE ALL ON public.cohort_agent_credentials FROM anon, authenticated;

COMMIT;
