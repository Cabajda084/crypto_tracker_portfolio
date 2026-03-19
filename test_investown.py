from investown_service import (
    init_investown_tables,
    add_investown_project,
    get_investown_projects,
    get_investown_schedule,
)

init_investown_tables()

add_investown_project(
    project_name="Test projekt",
    invested_amount=50000,
    investment_date="2026-03-01",
    first_payout_date="2026-04-01",
    duration_months=12,
    expected_yield_pa=8.7,
)

projects = get_investown_projects()
print("PROJEKTY:")
print(projects)

if projects:
    last_project_id = projects[-1][0]
    schedule = get_investown_schedule(last_project_id)

    print("\nKALENDÁŘ:")
    for row in schedule:
        print(row)