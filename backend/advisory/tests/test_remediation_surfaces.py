"""Actual API/database contracts for previously unexercised audit surfaces."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


class RemainingSurfaceTests(TestCase):
    def setUp(self):
        self.api = APIClient()

    def test_language_detection_is_state_mapping_not_free_text_nlp(self):
        response = self.api.get('/api/languages/detect/', {'state': 'Tamil Nadu'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['language_code'], 'ta')

    def test_bodo_api_alias_and_catalog_agree(self):
        response = self.api.get('/api/languages/normalise/', {'lang': 'bo'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['normalised'], 'brx')
        codes = [row['code'] for row in self.api.get('/api/languages/').data['languages']]
        self.assertIn('brx', codes)
        self.assertNotIn('bo', codes)

    def test_logout_acknowledges_client_cleanup_without_a_token(self):
        response = self.api.post('/api/users/logout/', {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

    @override_settings(STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    })
    def test_admin_requires_staff_and_has_a_real_index(self):
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        user = get_user_model().objects.create_user('audit-synthetic-staff', is_staff=True)
        self.client.force_login(user)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/index.html')
        self.assertContains(response, 'KrishiMitra Admin')

    def test_exact_market_requires_a_selected_mandi(self):
        response = self.api.get('/api/market-prices/mandi-prices/')
        self.assertEqual(response.status_code, 400)
