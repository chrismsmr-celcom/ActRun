-- Cohort organization membership bootstrap.
-- Apply in Supabase SQL Editor before enabling COHORT_ORGANIZATION_ID.
CREATE TABLE IF NOT EXISTS public.cohort_organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.cohort_memberships (
    organization_id UUID NOT NULL REFERENCES public.cohort_organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'invited', 'suspended')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_cohort_memberships_user
    ON public.cohort_memberships(user_id, status);

ALTER TABLE public.cohort_organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cohort_memberships ENABLE ROW LEVEL SECURITY;

-- Authenticated users can see only their own membership rows.
DROP POLICY IF EXISTS cohort_memberships_read_self ON public.cohort_memberships;
CREATE POLICY cohort_memberships_read_self
    ON public.cohort_memberships
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

-- Organization rows are visible only to active members.
DROP POLICY IF EXISTS cohort_organizations_read_member ON public.cohort_organizations;
CREATE POLICY cohort_organizations_read_member
    ON public.cohort_organizations
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.cohort_memberships m
            WHERE m.organization_id = id
              AND m.user_id = auth.uid()
              AND m.status = 'active'
        )
    );

-- Provision organizations and memberships through trusted admin tooling only.
REVOKE INSERT, UPDATE, DELETE ON public.cohort_organizations FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE ON public.cohort_memberships FROM anon, authenticated;
