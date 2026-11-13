# Lab Session 4 (and Migration/Query Verification) — Evidence & Terminal Outputs

## 1. Environment & Migration Status (`Step A1 & A2`)

```text
$ python manage.py check
System check identified no issues (0 silenced).

$ python manage.py showmigrations requests_app
requests_app
 [X] 0001_initial
 [X] 0002_servicerequest_due_at_and_more
```

Confirmed model fields:
```text
ServiceRequest: ['id', 'requester', 'category', 'title', 'description', 'location', 'priority', 'status', 'resolved_at', 'due_at', 'resolution_summary', 'created_at', 'updated_at']
WorkOrder:      ['id', 'service_request', 'technician', 'work_notes', 'started_at', 'completed_at', 'created_at']
Comment:        ['id', 'service_request', 'author', 'body', 'is_internal', 'created_at']
```

---

## 2. Form Layer Validation Evidence (`Step B2`)

```text
=== STEP B2: FORM VALIDATION ===
is_valid: False
errors: {
  "category": [{"message": "This field is required.", "code": "required"}],
  "title": [{"message": "Use at least 8 characters.", "code": ""}],
  "description": [{"message": "This field is required.", "code": "required"}],
  "location": [{"message": "This field is required.", "code": "required"}]
}
```

---

## 3. Row-Level Visibility Evidence (`Step C2`)

```text
=== STEP C2: ROW-LEVEL VISIBILITY ===
Item UUID: 18655e47-4827-4923-81f7-0f0322e1a5ab
Owner visible: True
Other visible: False
Staff visible: True
```

---

## 4. Transaction Rollback Proof (`Part K — Step K1`)

```text
=== STEP K1: TRANSACTION ROLLBACK PROOF ===
Caught: Deliberate failure for rollback test
status: open -> open
work orders: 0 -> 0
```
Both writes (`WorkOrder.objects.create` and `item.save(update_fields=["status", "updated_at"])`) rolled back atomically when `RuntimeError` was raised inside `with transaction.atomic():`.

---

## 5. Query Analysis & MySQL `EXPLAIN` Output

Querying open or assigned requests in one category (`ICT Support`, `category_id = 2`) ordered by `priority` and `created_at`:

```sql
SELECT `requests_app_servicerequest`.`id`,
       `requests_app_servicerequest`.`requester_id`,
       `requests_app_servicerequest`.`category_id`,
       `requests_app_servicerequest`.`title`,
       `requests_app_servicerequest`.`description`,
       `requests_app_servicerequest`.`location`,
       `requests_app_servicerequest`.`priority`,
       `requests_app_servicerequest`.`status`,
       `requests_app_servicerequest`.`resolved_at`,
       `requests_app_servicerequest`.`due_at`,
       `requests_app_servicerequest`.`resolution_summary`,
       `requests_app_servicerequest`.`created_at`,
       `requests_app_servicerequest`.`updated_at`
FROM `requests_app_servicerequest`
WHERE (`requests_app_servicerequest`.`category_id` = 2
  AND `requests_app_servicerequest`.`status` IN ('open', 'assigned'))
ORDER BY `requests_app_servicerequest`.`priority` ASC,
         `requests_app_servicerequest`.`created_at` ASC
```

MySQL 8.0.46 `queryset.explain()` output:
```text
-> Sort row IDs: requests_app_servicerequest.priority, requests_app_servicerequest.created_at  (cost=2.76 rows=5)
    -> Index range scan on requests_app_servicerequest using req_cat_status_idx over (category_id = 2 AND status = 'assigned') OR (category_id = 2 AND status = 'open'), with index condition: ((requests_app_servicerequest.category_id = 2) and (requests_app_servicerequest.`status` in ('open','assigned')))  (cost=2.76 rows=5)
```
**Index Analysis**: MySQL selected the composite index `req_cat_status_idx` (`fields=("category", "status")`) via an **Index range scan** over `(category_id = 2 AND status = 'assigned') OR (category_id = 2 AND status = 'open')`, then sorted the matching rows by `(priority, created_at)`.

---

## 6. Automated Test Suite Output (`Part L & Part M Task 5`)

```text
$ python manage.py test requests_app.tests -v 2
Creating test database for alias 'default' ('file:memorydb_default?mode=memory&cache=shared')...
Found 20 test(s).
...
test_assigned_technician_resolution_changes_both_models (requests_app.tests.test_request_crud.ServiceRequestCrudTests.test_assigned_technician_resolution_changes_both_models) ... ok
test_filtered_pagination_preserves_q_and_status (requests_app.tests.test_request_crud.ServiceRequestCrudTests.test_filtered_pagination_preserves_q_and_status) ... ok
test_invalid_post_does_not_create_request (requests_app.tests.test_request_crud.ServiceRequestCrudTests.test_invalid_post_does_not_create_request) ... ok
test_list_requires_login (requests_app.tests.test_request_crud.ServiceRequestCrudTests.test_list_requires_login) ... ok
test_non_staff_assignment_returns_403_and_creates_no_work_order (requests_app.tests.test_request_crud.ServiceRequestCrudTests.test_non_staff_assignment_returns_403_and_creates_no_work_order) ... ok
test_other_requester_receives_404 (requests_app.tests.test_request_crud.ServiceRequestCrudTests.test_other_requester_receives_404) ... ok
test_owner_can_open_detail (requests_app.tests.test_request_crud.ServiceRequestCrudTests.test_owner_can_open_detail) ... ok
test_resolution_without_assignment_leaves_request_unchanged (requests_app.tests.test_request_crud.ServiceRequestCrudTests.test_resolution_without_assignment_leaves_request_unchanged) ... ok
test_staff_assignment_creates_one_work_order_and_sets_assigned (requests_app.tests.test_request_crud.ServiceRequestCrudTests.test_staff_assignment_creates_one_work_order_and_sets_assigned) ... ok
test_summary_counts_respect_visibility (requests_app.tests.test_request_crud.ServiceRequestCrudTests.test_summary_counts_respect_visibility) ... ok
test_valid_post_creates_request_for_logged_in_user (requests_app.tests.test_request_crud.ServiceRequestCrudTests.test_valid_post_creates_request_for_logged_in_user) ... ok
test_category_in_use_is_protected (requests_app.tests.test_models.ServiceRequestModelTests.test_category_in_use_is_protected) ... ok
test_closed_without_summary_or_timestamp_fails_clean (requests_app.tests.test_models.ServiceRequestModelTests.test_closed_without_summary_or_timestamp_fails_clean) ... ok
test_database_constraint_rejects_priority_six (requests_app.tests.test_models.ServiceRequestModelTests.test_database_constraint_rejects_priority_six) ... ok
test_default_status_is_open (requests_app.tests.test_models.ServiceRequestModelTests.test_default_status_is_open) ... ok
test_due_at_filtering (requests_app.tests.test_models.ServiceRequestModelTests.test_due_at_filtering) ... ok
test_priority_validator_rejects_zero (requests_app.tests.test_models.ServiceRequestModelTests.test_priority_validator_rejects_zero) ... ok
test_request_accepts_only_one_work_order (requests_app.tests.test_models.ServiceRequestModelTests.test_request_accepts_only_one_work_order) ... ok
test_resolved_without_summary_or_timestamp_fails_clean (requests_app.tests.test_models.ServiceRequestModelTests.test_resolved_without_summary_or_timestamp_fails_clean) ... ok
test_valid_resolved_passes_clean (requests_app.tests.test_models.ServiceRequestModelTests.test_valid_resolved_passes_clean) ... ok

----------------------------------------------------------------------
Ran 20 tests in 15.960s

OK
```

