from uuid import UUID

import pytest

from cerbere_cohort.postgres import PostgresPersistentWorkspace, _Connection


ORG_A = "11111111-1111-4111-8111-111111111111"
ORG_B = "22222222-2222-4222-8222-222222222222"


def test_organization_ids_map_to_distinct_valid_postgres_schemas():
    schema_a = f"cohort_org_{UUID(ORG_A).hex}"
    schema_b = f"cohort_org_{UUID(ORG_B).hex}"

    assert schema_a != schema_b
    assert _Connection._translate("SELECT * FROM events", schema_a) == (
        f"SELECT * FROM {schema_a}.cohort_events"
    )
    assert _Connection._translate("SELECT * FROM events", schema_b) == (
        f"SELECT * FROM {schema_b}.cohort_events"
    )


def test_all_runtime_tables_are_routed_to_the_organization_schema():
    schema = f"cohort_org_{UUID(ORG_A).hex}"
    statements = [
        "SELECT * FROM objects",
        "SELECT * FROM events ORDER BY rowid",
        "SELECT * FROM leases",
        "SELECT * FROM metadata",
        "SELECT * FROM lease_counters",
        "SELECT * FROM api_branches",
    ]

    translated = [_Connection._translate(sql, schema) for sql in statements]
    assert all(schema + ".cohort_" in sql for sql in translated)
    assert all("public.cohort_" not in sql for sql in translated)


def test_invalid_schema_name_is_rejected_before_connecting():
    with pytest.raises(ValueError, match="Invalid PostgreSQL schema name"):
        _Connection.__new__(_Connection)._validate_schema("bad-name; DROP SCHEMA public")


def test_workspace_derives_schema_from_canonical_organization_uuid():
    workspace = PostgresPersistentWorkspace.__new__(PostgresPersistentWorkspace)
    workspace.organization_id = str(UUID(ORG_A))
    workspace.schema = f"cohort_org_{UUID(ORG_A).hex}"

    assert workspace.schema == "cohort_org_11111111111141118111111111111111"
