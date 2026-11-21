-- Cohort workspace onboarding: organization profile and idempotent first-workspace setup.
BEGIN;

ALTER TABLE public.cohort_organizations
    ADD COLUMN IF NOT EXISTS account_type TEXT NOT NULL DEFAULT 'individual'
        CHECK (account_type IN ('individual', 'team', 'enterprise')),
    ADD COLUMN IF NOT EXISTS company_size TEXT
        CHECK (company_size IS NULL OR company_size IN ('1-10', '10-100', '100+')),
    ADD COLUMN IF NOT EXISTS industry TEXT,
    ADD COLUMN IF NOT EXISTS primary_use_case TEXT,
    ADD COLUMN IF NOT EXISTS expected_agents TEXT
        CHECK (expected_agents IS NULL OR expected_agents IN ('1-5', '6-20', '21-100', '100+')),
    ADD COLUMN IF NOT EXISTS frameworks TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    ADD COLUMN IF NOT EXISTS onboarding_completed_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS public.cohort_user_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL CHECK (length(full_name) BETWEEN 1 AND 120),
    job_title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.cohort_user_profiles ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.cohort_user_profiles FROM anon, authenticated;

-- Existing workspaces predate the onboarding flow; do not block invited members
-- from accessing them. New signup-trigger workspaces keep NULL until onboarding.
UPDATE public.cohort_organizations
SET onboarding_completed_at = created_at
WHERE onboarding_completed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_cohort_org_onboarding
    ON public.cohort_organizations(onboarding_completed_at);

COMMIT;
