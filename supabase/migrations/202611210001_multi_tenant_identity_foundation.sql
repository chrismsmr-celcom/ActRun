-- Multi-tenant identity foundation: personal workspaces, contextual RBAC,
-- audit trail, verified domains and per-workspace SSO configuration.
-- Runtime traffic must not be enabled until the API resolves persistence per workspace.
BEGIN;

ALTER TABLE public.cohort_memberships
    DROP CONSTRAINT IF EXISTS cohort_memberships_role_check;
ALTER TABLE public.cohort_memberships
    ADD CONSTRAINT cohort_memberships_role_check
    CHECK (role IN ('owner', 'admin', 'member', 'guest', 'viewer', 'custom'));

ALTER TABLE public.cohort_memberships
    ADD COLUMN IF NOT EXISTS custom_role_id UUID;

CREATE TABLE IF NOT EXISTS public.cohort_permissions (
    key TEXT PRIMARY KEY,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS public.cohort_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.cohort_organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 80),
    is_system BOOLEAN NOT NULL DEFAULT false,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, name),
    UNIQUE (id, organization_id)
);

ALTER TABLE public.cohort_memberships
    DROP CONSTRAINT IF EXISTS cohort_memberships_custom_role_fk;
ALTER TABLE public.cohort_memberships
    ADD CONSTRAINT cohort_memberships_custom_role_fk
    FOREIGN KEY (custom_role_id, organization_id)
    REFERENCES public.cohort_roles(id, organization_id)
    ON DELETE NO ACTION;

CREATE TABLE IF NOT EXISTS public.cohort_role_permissions (
    role_id UUID NOT NULL REFERENCES public.cohort_roles(id) ON DELETE CASCADE,
    permission_key TEXT NOT NULL REFERENCES public.cohort_permissions(key) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_key)
);

INSERT INTO public.cohort_permissions(key, description) VALUES
    ('workspace:read', 'Read workspace resources'),
    ('workspace:update', 'Update workspace settings'),
    ('workspace:delete', 'Delete the workspace'),
    ('member:read', 'View workspace members'),
    ('member:invite', 'Invite workspace members'),
    ('member:manage', 'Change roles and remove members'),
    ('project:create', 'Create projects'),
    ('project:delete', 'Delete projects'),
    ('agent:manage', 'Create and revoke agent credentials'),
    ('billing:read', 'View billing information'),
    ('billing:update', 'Manage billing information'),
    ('audit:read', 'Read workspace audit logs')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.cohort_audit_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES public.cohort_organizations(id) ON DELETE CASCADE,
    actor_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cohort_audit_org_created
    ON public.cohort_audit_logs(organization_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.cohort_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.cohort_organizations(id) ON DELETE CASCADE,
    domain TEXT NOT NULL,
    verified_at TIMESTAMPTZ,
    auto_join BOOLEAN NOT NULL DEFAULT false,
    require_admin_approval BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, domain),
    UNIQUE (domain)
);

CREATE TABLE IF NOT EXISTS public.cohort_sso_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL UNIQUE REFERENCES public.cohort_organizations(id) ON DELETE CASCADE,
    protocol TEXT NOT NULL CHECK (protocol IN ('saml', 'oidc')),
    issuer TEXT NOT NULL,
    metadata_url TEXT,
    client_id TEXT,
    encrypted_client_secret BYTEA,
    enabled BOOLEAN NOT NULL DEFAULT false,
    enforce_sso BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One personal workspace is provisioned atomically for each new Supabase identity.
CREATE OR REPLACE FUNCTION public.cohort_provision_personal_workspace()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    new_workspace_id UUID;
    workspace_name TEXT;
BEGIN
    workspace_name := COALESCE(
        NULLIF(split_part(COALESCE(NEW.email, ''), '@', 1), ''),
        'Personal workspace'
    );
    INSERT INTO public.cohort_organizations(name)
    VALUES (workspace_name || '''s workspace')
    RETURNING id INTO new_workspace_id;

    INSERT INTO public.cohort_memberships(organization_id, user_id, role, status)
    VALUES (new_workspace_id, NEW.id, 'owner', 'active');

    INSERT INTO public.cohort_audit_logs(
        organization_id, actor_user_id, action, target_type, target_id
    ) VALUES (
        new_workspace_id, NEW.id, 'workspace.created', 'workspace', new_workspace_id::text
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS cohort_auth_user_workspace_bootstrap ON auth.users;
CREATE TRIGGER cohort_auth_user_workspace_bootstrap
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.cohort_provision_personal_workspace();

-- Backfill existing accounts that predate automatic workspace provisioning.
WITH users_without_workspace AS (
    SELECT u.id, COALESCE(
        NULLIF(split_part(COALESCE(u.email, ''), '@', 1), ''),
        'Personal workspace'
    ) AS workspace_name
    FROM auth.users u
    WHERE NOT EXISTS (
        SELECT 1 FROM public.cohort_memberships m
        WHERE m.user_id = u.id AND m.status = 'active'
    )
),
created_workspaces AS (
    INSERT INTO public.cohort_organizations(name)
    SELECT workspace_name || '''s workspace'
    FROM users_without_workspace
    RETURNING id, name
)
INSERT INTO public.cohort_memberships(organization_id, user_id, role, status)
SELECT w.id, u.id, 'owner', 'active'
FROM created_workspaces w
JOIN users_without_workspace u
  ON w.name = u.workspace_name || '''s workspace'
WHERE NOT EXISTS (
    SELECT 1 FROM public.cohort_memberships m
    WHERE m.user_id = u.id AND m.status = 'active'
);

ALTER TABLE public.cohort_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cohort_role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cohort_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cohort_domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cohort_sso_configs ENABLE ROW LEVEL SECURITY;

-- Sensitive mutations remain server-only. The browser can read only the
-- permission catalog; workspace-scoped administration goes through the API.
GRANT SELECT ON public.cohort_permissions TO authenticated;
REVOKE ALL ON public.cohort_roles FROM anon, authenticated;
REVOKE ALL ON public.cohort_role_permissions FROM anon, authenticated;
REVOKE ALL ON public.cohort_audit_logs FROM anon, authenticated;
REVOKE ALL ON public.cohort_domains FROM anon, authenticated;
REVOKE ALL ON public.cohort_sso_configs FROM anon, authenticated;

COMMIT;
