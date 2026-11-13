# VUA-SEN305 Lab Session 4 — Practical Report Sheet & Submission Package

## Group & Submission Details

| Field | Details |
| :--- | :--- |
| **Project Repository Link** | https://github.com/patriarchpam/sen305-entreprise-platform.git |
| **Group Name** | Enterprise Platform |
| **Group Leader** | Pam Patriarch Yeipyeng |
| **Student Name** | Pam Patriarch Yeipyeng |
| **Registration Number** | VUG/SEN/24/12478 |
| **Date** | 2026-11-13 |
| **Branch** | `feature/server-rendered-crud` |
| **Commit Hash** | `4b4b0cb` |
| **MySQL Version** | `8.0.46` |
| **Django Version** | `5.2.18` |
| **Passing Tests** | `20 / 20` (`requests_app.tests`) |

---

## In-Lab Exercise Verification (Tasks 1, 2 & 3 from Google Classroom)

### Task 1 — Add Service Level Due Date
1. **`due_at` field**: Added `due_at = models.DateTimeField(null=True, blank=True)` to `ServiceRequest` in `requests_app/models.py` (line 55).
2. **Supporting Index**: Added `models.Index(fields=("status", "due_at"), name="req_status_due_idx")` in `ServiceRequest.Meta.indexes` (line 65).
3. **Migration `0002`**: Generated and applied `requests_app/migrations/0002_servicerequest_due_at_and_more.py` without modifying `0001_initial.py`.
4. **Admin Update**: Displayed `due_at` in `ServiceRequestAdmin.list_display` and added `OverdueFilter(admin.SimpleListFilter)` in `requests_app/admin.py` (lines 6–27, 45–55).
5. **Due Date Query**: Verified in `test_due_at_filtering` (`requests_app/tests/test_models.py`, lines 92–100) by creating two requests with different due dates (`now + 1 day` and `now + 7 days`) and querying `ServiceRequest.objects.filter(due_at__lte=cutoff)`.

### Task 2 — Add Resolution Summary
6. **`resolution_summary` field**: Added `resolution_summary = models.TextField(blank=True)` to `ServiceRequest` in `requests_app/models.py` (line 56).
7. **Domain Model Validation (`clean()`)**: Implemented `ServiceRequest.clean()` in `requests_app/models.py` (lines 74–83) and enforced in `service_request_resolve` (`requests_app/services.py`) so `RESOLVED` or `CLOSED` requests require both `resolved_at` and a non-empty `resolution_summary`.
8. **Proved with `full_clean()` & Automated Tests**:
   - `test_resolved_without_summary_or_timestamp_fails_clean`
   - `test_closed_without_summary_or_timestamp_fails_clean`
   - `test_valid_resolved_passes_clean`
9. **Domain Layer Placement**: Validation lives in `ServiceRequest.clean()` (domain model) and `requests_app/services.py` (service layer), not only in Django Admin.

### Task 3 — Analyse a Query
Created synthetic service requests across two categories (`ICT Support` and `Electrical`) and three statuses (`open`, `assigned`, `resolved`), then ran:
```python
qs = ServiceRequest.objects.filter(
    category=category,
    status__in=[ServiceRequest.Status.OPEN, ServiceRequest.Status.ASSIGNED],
).order_by("priority", "created_at")
print(qs.query)
print(qs.explain())
```
- **Generated SQL (`queryset.query`)**:
  ```sql
  SELECT `requests_app_servicerequest`.`id`, `requests_app_servicerequest`.`requester_id`,
         `requests_app_servicerequest`.`category_id`, `requests_app_servicerequest`.`title`,
         `requests_app_servicerequest`.`description`, `requests_app_servicerequest`.`location`,
         `requests_app_servicerequest`.`priority`, `requests_app_servicerequest`.`status`,
         `requests_app_servicerequest`.`resolved_at`, `requests_app_servicerequest`.`due_at`,
         `requests_app_servicerequest`.`resolution_summary`, `requests_app_servicerequest`.`created_at`,
         `requests_app_servicerequest`.`updated_at`
  FROM `requests_app_servicerequest`
  WHERE (`requests_app_servicerequest`.`category_id` = 2
    AND `requests_app_servicerequest`.`status` IN ('open', 'assigned'))
  ORDER BY `requests_app_servicerequest`.`priority` ASC,
           `requests_app_servicerequest`.`created_at` ASC
  ```
- **MySQL 8.0.46 `queryset.explain()` Output**:
  ```text
  -> Sort row IDs: requests_app_servicerequest.priority, requests_app_servicerequest.created_at  (cost=2.76 rows=5)
      -> Index range scan on requests_app_servicerequest using req_cat_status_idx over (category_id = 2 AND status = 'assigned') OR (category_id = 2 AND status = 'open'), with index condition: ((requests_app_servicerequest.category_id = 2) and (requests_app_servicerequest.`status` in ('open','assigned')))  (cost=2.76 rows=5)
  ```
- **Index Analysis**: MySQL uses the composite index **`req_cat_status_idx`** (`(category_id, status)`) via an **Index range scan** to filter matching rows in one category across the `open` and `assigned` statuses, followed by an in-memory filesort (`Sort row IDs`) on `(priority, created_at)`.

### Exercise Acceptance Criteria Checklist

| Criterion | Pass Condition | Status / Evidence |
| :--- | :--- | :--- |
| **Migration discipline** | A reviewed `0002` migration applies successfully | `[X] 0002_servicerequest_due_at_and_more` applied; `0001_initial.py` untouched |
| **Due date** | Field and supporting index exist in MySQL | `due_at` column and `req_status_due_idx` present in MySQL |
| **Resolution rule** | Invalid resolved records fail `full_clean()` | Verified in `ServiceRequest.clean()` and unit tests |
| **Admin** | Due date and resolution data are visible and searchable or filterable | `due_at` in `list_display`/`list_filter`, `OverdueFilter`, and `resolution_summary` in `search_fields` |
| **Query evidence** | Generated SQL and explain output are recorded | Recorded above (`req_cat_status_idx` index range scan) |
| **Tests** | Original and new tests pass | `20 / 20` tests pass |
| **Data safety** | Only synthetic laboratory data are used | Only synthetic lab accounts and requests used |

---

## Observed Results (Part J & Part L)

| Test | Expected | Observed |
| :--- | :--- | :--- |
| **Anonymous list** | `302` to login | `302` redirect to `/accounts/login/?next=/requests/` |
| **Owner detail** | `200` | `200 OK` (renders request title, metadata, and comments) |
| **Other requester detail** | `404` | `404 Not Found` (no owner data disclosed) |
| **Invalid create** | `200`; no row | `200 OK`; inline error `"Use at least 8 characters."`; row count unchanged |
| **Valid create** | `302`; one row | `302` redirect to `/requests/<uuid>/`; 1 row created with `requester=request.user` |
| **Rollback** | No state change | `RuntimeError` caught outside atomic block; `status: open -> open`, `work orders: 0 -> 0` |
| **Full test suite** | All pass | `Ran 20 tests ... OK` (all 9 model/migration tests + 11 CRUD/workflow/authorization tests pass) |

---

## Part J — Database Verification Record

| Evidence | Student Record |
| :--- | :--- |
| **Valid request UUID** | `18655e47-4827-4923-81f7-0f0322e1a5ab` |
| **Invalid form error** | `{"title": [{"message": "Use at least 8 characters.", "code": ""}]}` |
| **Owner edit result** | `200 OK` / `302` redirect to detail showing updated title and location |
| **Other requester response** | `404 Not Found` |
| **Comment author** | `requester1` / `technician1` (automatically set from `request.user`) |
| **PRG confirmed** | Every successful `POST` returns `302 Found` redirecting to `requests:detail`; browser Back does not duplicate rows |

---

## Architecture Explanation: Forms / Selectors / Services / Views Separation

1. **Forms (`requests_app/forms.py`)**: Expose only safe user-editable fields (`category`, `title`, `description`, `location`, `priority` in `ServiceRequestForm`; `body` in `CommentForm`; active staff `technician` in `AssignmentForm`; required `work_notes` in `ResolutionForm`). Sensitive fields (`requester`, `status`, `resolved_at`, `author`, `is_internal`) are excluded so users cannot spoof ownership or bypass workflow state transitions via crafted POST payloads.
2. **Selectors (`requests_app/selectors.py`)**: Centralize read queries (`service_request_list`, `service_request_filter`, `service_request_get`, `service_request_summary_counts`). They optimize queries with `select_related("requester", "category")` and `annotate(comment_count=Count("comments"))` to prevent N+1 queries, and enforce row-level authorization (`queryset if user.is_staff else queryset.filter(requester=user)`).
3. **Services (`requests_app/services.py`)**: Encapsulate all domain write operations (`service_request_create`, `service_request_update`, `comment_create`, `service_request_assign`, `service_request_resolve`) inside `@transaction.atomic` blocks using `select_for_update()` row locking and `full_clean()` model validation.
4. **Views (`requests_app/views.py`)**: Parse HTTP parameters, invoke selectors/forms/services, attach user feedback via `django.contrib.messages`, and return `HttpResponse` or `HttpResponseRedirect` following the POST/Redirect/GET (PRG) pattern.

---

## Short Reflection Answers

### 1. What rule belongs in the service layer rather than the view?
Multi-model workflow transitions and invariant enforcement belong in the service layer:
- Only an `OPEN` request can be edited by a non-staff requester (`service_request_update`).
- Completed (`RESOLVED` or `CLOSED`) requests cannot be assigned (`service_request_assign`).
- Resolving a request requires an existing `WorkOrder` with an assigned technician, restricted to the assigned technician or staff, and must atomically update both `WorkOrder` (`work_notes`, `completed_at`) and `ServiceRequest` (`status=RESOLVED`, `resolved_at`, `resolution_summary`) (`service_request_resolve`).

### 2. How did the selector prevent object-level data leakage?
`service_request_list(*, user)` filters the base `ServiceRequest` queryset with `.filter(requester=user)` whenever `user.is_staff` is `False`. Because `service_request_get(*, user, request_id)` queries through `service_request_list(user=user).get(id=request_id)`, any attempt by another non-staff user (`requester2`) to load an unowned request UUID raises `ServiceRequest.DoesNotExist`, which the view converts into a `404 Not Found` without revealing whether the UUID exists.

### 3. What two database changes had to succeed or fail together?
1. **During Assignment (`service_request_assign`)**: Creating/updating the `WorkOrder` record (assigning `technician`) and updating `ServiceRequest.status` to `ASSIGNED`.
2. **During Resolution (`service_request_resolve`)**: Updating `WorkOrder` (`work_notes` and `completed_at`) and updating `ServiceRequest` (`status = RESOLVED`, `resolved_at`, and `resolution_summary`). Wrapping both inside `@transaction.atomic` with `select_for_update()` ensures no partial state can persist if validation or a database error occurs.

### 4. Which test catches a future authorization regression?
- `test_other_requester_receives_404` catches regressions in object-level read isolation (ensuring a logged-in user cannot view another user's request detail page).
- `test_non_staff_assignment_returns_403_and_creates_no_work_order` catches regressions in role-based mutation authorization (ensuring non-staff users receive HTTP `403 Forbidden` and cannot create a `WorkOrder`).
- `test_list_requires_login` catches regressions in authentication protection for the request list endpoint.

