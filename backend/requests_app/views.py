from urllib.parse import urlencode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from .forms import AssignmentForm, CommentForm, ResolutionForm, ServiceRequestForm
from .models import ServiceRequest, WorkOrder
from .selectors import (
    service_request_filter,
    service_request_get,
    service_request_summary_counts,
)
from .services import (
    comment_create,
    service_request_assign,
    service_request_create,
    service_request_resolve,
    service_request_update,
)


@login_required
def request_list(request):
    status = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()
    queryset = service_request_filter(user=request.user, status=status, query=query)
    summary_counts = service_request_summary_counts(user=request.user)
    page_obj = Paginator(queryset, 10).get_page(request.GET.get("page"))

    filter_params = {}
    if query:
        filter_params["q"] = query
    if status:
        filter_params["status"] = status
    filter_query = urlencode(filter_params)

    return render(request, "requests_app/request_list.html", {
        "page_obj": page_obj,
        "status_choices": ServiceRequest.Status.choices,
        "selected_status": status,
        "query": query,
        "summary_counts": summary_counts,
        "filter_query": filter_query,
    })


@login_required
def request_detail(request, request_id):
    try:
        item = service_request_get(user=request.user, request_id=request_id)
    except ServiceRequest.DoesNotExist as exc:
        raise Http404("Service request not found.") from exc

    work_order = (
        WorkOrder.objects.select_related("technician")
        .filter(service_request=item)
        .first()
    )
    can_assign = request.user.is_staff
    can_resolve = bool(
        request.user.is_staff
        or (work_order and work_order.technician_id == request.user.id)
    )

    assign_form = (
        AssignmentForm(
            initial={"technician": work_order.technician_id} if work_order else None
        )
        if can_assign
        else None
    )
    resolve_form = (
        ResolutionForm(
            initial={"work_notes": work_order.work_notes} if work_order else None
        )
        if can_resolve
        else None
    )

    return render(request, "requests_app/request_detail.html", {
        "item": item,
        "work_order": work_order,
        "comments": item.comments.select_related("author").order_by("created_at"),
        "comment_form": CommentForm(),
        "can_assign": can_assign,
        "can_resolve": can_resolve,
        "assign_form": assign_form,
        "resolve_form": resolve_form,
    })


@login_required
def request_create(request):
    form = ServiceRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = service_request_create(requester=request.user, **form.cleaned_data)
        messages.success(request, "Service request created.")
        return redirect("requests:detail", request_id=item.id)
    return render(request, "requests_app/request_form.html", {"form": form, "mode": "Create"})


@login_required
def request_update(request, request_id):
    try:
        item = service_request_get(user=request.user, request_id=request_id)
    except ServiceRequest.DoesNotExist as exc:
        raise Http404("Service request not found.") from exc
    form = ServiceRequestForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        try:
            item = service_request_update(item=item, actor=request.user, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Service request updated.")
            return redirect("requests:detail", request_id=item.id)
    return render(request, "requests_app/request_form.html", {
        "form": form, "mode": "Update", "item": item
    })


@require_POST
@login_required
def comment_add(request, request_id):
    try:
        item = service_request_get(user=request.user, request_id=request_id)
    except ServiceRequest.DoesNotExist as exc:
        raise Http404("Service request not found.") from exc
    form = CommentForm(request.POST)
    if form.is_valid():
        comment_create(item=item, author=request.user, **form.cleaned_data)
        messages.success(request, "Comment added.")
    else:
        messages.error(request, "Enter at least 3 characters.")
    return redirect("requests:detail", request_id=item.id)


@require_POST
@login_required
def request_assign(request, request_id):
    if not request.user.is_staff:
        raise PermissionDenied("Staff access is required.")
    try:
        item = service_request_get(user=request.user, request_id=request_id)
    except ServiceRequest.DoesNotExist as exc:
        raise Http404("Service request not found.") from exc

    form = AssignmentForm(request.POST)
    if form.is_valid():
        try:
            service_request_assign(
                item=item,
                technician=form.cleaned_data["technician"],
                actor=request.user,
            )
        except ValidationError as exc:
            for msg in exc.messages:
                messages.error(request, msg)
        else:
            messages.success(request, "Technician assigned.")
    else:
        for field_errors in form.errors.values():
            for err in field_errors:
                messages.error(request, err)
    return redirect("requests:detail", request_id=item.id)


@require_POST
@login_required
def request_resolve(request, request_id):
    try:
        item = service_request_get(user=request.user, request_id=request_id)
    except ServiceRequest.DoesNotExist as exc:
        raise Http404("Service request not found.") from exc

    form = ResolutionForm(request.POST)
    if form.is_valid():
        try:
            service_request_resolve(
                item=item,
                actor=request.user,
                work_notes=form.cleaned_data["work_notes"],
            )
        except ValidationError as exc:
            for msg in exc.messages:
                messages.error(request, msg)
        else:
            messages.success(request, "Service request resolved.")
    else:
        for field_errors in form.errors.values():
            for err in field_errors:
                messages.error(request, err)
    return redirect("requests:detail", request_id=item.id)
