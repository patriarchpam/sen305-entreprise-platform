from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from requests_app.models import Category, ServiceRequest, WorkOrder
from requests_app.services import service_request_assign


class ServiceRequestCrudTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="pass12345")
        self.other = User.objects.create_user("other", password="pass12345")
        self.staff = User.objects.create_user(
            "staff_tech", password="pass12345", is_staff=True
        )
        self.category = Category.objects.create(name="Facilities")
        self.item = ServiceRequest.objects.create(
            requester=self.owner,
            category=self.category,
            title="Projector does not display",
            description="The projector reports no HDMI signal.",
            location="Room B12",
            priority=3,
        )

    def test_list_requires_login(self):
        response = self.client.get(reverse("requests:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_owner_can_open_detail(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("requests:detail", args=[self.item.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.item.title)

    def test_other_requester_receives_404(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("requests:detail", args=[self.item.id]))
        self.assertEqual(response.status_code, 404)

    def test_valid_post_creates_request_for_logged_in_user(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("requests:create"), {
            "category": self.category.id,
            "title": "Air conditioner leaks water",
            "description": "Water drips near the laboratory entrance.",
            "location": "Software Laboratory",
            "priority": 1,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ServiceRequest.objects.filter(
            requester=self.owner, title="Air conditioner leaks water"
        ).exists())

    def test_invalid_post_does_not_create_request(self):
        self.client.force_login(self.owner)
        before = ServiceRequest.objects.count()
        response = self.client.post(reverse("requests:create"), {
            "category": self.category.id,
            "title": "Short",
            "description": "",
            "location": "",
            "priority": 1,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ServiceRequest.objects.count(), before)
        self.assertContains(response, "Use at least 8 characters.")

    # --- Part M Task 5 Tests ---

    def test_non_staff_assignment_returns_403_and_creates_no_work_order(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("requests:assign", args=[self.item.id]),
            {"technician": self.staff.id},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(WorkOrder.objects.filter(service_request=self.item).count(), 0)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, ServiceRequest.Status.OPEN)

    def test_staff_assignment_creates_one_work_order_and_sets_assigned(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("requests:assign", args=[self.item.id]),
            {"technician": self.staff.id},
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, ServiceRequest.Status.ASSIGNED)
        self.assertEqual(WorkOrder.objects.filter(service_request=self.item).count(), 1)
        work_order = WorkOrder.objects.get(service_request=self.item)
        self.assertEqual(work_order.technician, self.staff)

    def test_resolution_without_assignment_leaves_request_unchanged(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("requests:resolve", args=[self.item.id]),
            {"work_notes": "Replaced HDMI cable and verified display."},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, ServiceRequest.Status.OPEN)
        self.assertIsNone(self.item.resolved_at)
        self.assertContains(response, "Assign a technician before resolving.")

    def test_assigned_technician_resolution_changes_both_models(self):
        service_request_assign(
            item=self.item, technician=self.staff, actor=self.staff
        )
        self.client.force_login(self.staff)
        notes = "Replaced faulty HDMI transmitter and tested projector."
        response = self.client.post(
            reverse("requests:resolve", args=[self.item.id]),
            {"work_notes": notes},
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        work_order = WorkOrder.objects.get(service_request=self.item)
        self.assertEqual(self.item.status, ServiceRequest.Status.RESOLVED)
        self.assertIsNotNone(self.item.resolved_at)
        self.assertEqual(self.item.resolution_summary, notes)
        self.assertEqual(work_order.work_notes, notes)
        self.assertIsNotNone(work_order.completed_at)

    def test_filtered_pagination_preserves_q_and_status(self):
        for i in range(12):
            ServiceRequest.objects.create(
                requester=self.owner,
                category=self.category,
                title=f"Network switch port failure {i + 1:02d}",
                description="Switch port drops packets intermittently.",
                location="Server Room",
                priority=2,
                status=ServiceRequest.Status.OPEN,
            )
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("requests:list"),
            {"q": "Network switch", "status": ServiceRequest.Status.OPEN, "page": 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 2 of 2")
        self.assertContains(response, 'value="Network switch"')
        self.assertContains(
            response,
            f'?q=Network+switch&amp;status={ServiceRequest.Status.OPEN}&page=1',
        )

    def test_summary_counts_respect_visibility(self):
        ServiceRequest.objects.create(
            requester=self.other,
            category=self.category,
            title="Other user request in lab",
            description="Only visible to other and staff.",
            location="Room C10",
            priority=3,
            status=ServiceRequest.Status.ASSIGNED,
        )
        self.client.force_login(self.owner)
        owner_resp = self.client.get(reverse("requests:list"))
        self.assertEqual(owner_resp.context["summary_counts"]["open_count"], 1)
        self.assertEqual(owner_resp.context["summary_counts"]["assigned_count"], 0)

        self.client.force_login(self.staff)
        staff_resp = self.client.get(reverse("requests:list"))
        self.assertEqual(staff_resp.context["summary_counts"]["open_count"], 1)
        self.assertEqual(staff_resp.context["summary_counts"]["assigned_count"], 1)
