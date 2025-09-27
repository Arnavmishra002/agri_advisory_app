# agri_advisory_app/advisory/tests.py

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from .models import Crop, CropAdvisory, User, ForumPost
from advisory.api.serializers import CropSerializer, CropAdvisorySerializer, UserSerializer, ForumPostSerializer
from advisory.api.views import UserViewSet, CropViewSet, CropAdvisoryViewSet, ForumPostViewSet

User = get_user_model()

class UserAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(username='admin', email='admin@example.com', password='adminpassword', role='admin')
        self.farmer_user = User.objects.create_user(username='farmer', email='farmer@example.com', password='farmerpassword', role='farmer')
        self.officer_user = User.objects.create_user(username='officer', email='officer@example.com', password='officerpassword', role='officer')

        self.user_list_url = reverse('user-list') # Assumes 'user-list' is the name for UserViewSet list endpoint

    def _get_token(self, username, password):
        login_url = reverse('token_obtain_pair')
        response = self.client.post(login_url, {'username': username, 'password': password}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data['access']

    def test_user_registration(self):
        data = {'username': 'newuser', 'email': 'new@example.com', 'password': 'newpassword'}
        response = self.client.post(self.user_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 4) # 3 existing + 1 new
        new_user = User.objects.get(username='newuser')
        self.assertEqual(new_user.role, 'farmer') # Default role

    def test_admin_can_list_users(self):
        admin_token = self._get_token('admin', 'adminpassword')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + admin_token)
        response = self.client.get(self.user_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3) # admin, farmer, officer

    def test_farmer_cannot_list_users(self):
        farmer_token = self._get_token('farmer', 'farmerpassword')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + farmer_token)
        response = self.client.get(self.user_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_retrieve_any_user(self):
        admin_token = self._get_token('admin', 'adminpassword')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + admin_token)
        detail_url = reverse('user-detail', kwargs={'pk': self.farmer_user.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'farmer')

    def test_farmer_can_retrieve_own_profile(self):
        farmer_token = self._get_token('farmer', 'farmerpassword')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + farmer_token)
        detail_url = reverse('user-detail', kwargs={'pk': self.farmer_user.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'farmer')

    def test_farmer_cannot_retrieve_other_profile(self):
        farmer_token = self._get_token('farmer', 'farmerpassword')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + farmer_token)
        detail_url = reverse('user-detail', kwargs={'pk': self.admin_user.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_any_user(self):
        admin_token = self._get_token('admin', 'adminpassword')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + admin_token)
        detail_url = reverse('user-detail', kwargs={'pk': self.farmer_user.pk})
        data = {'email': 'updated_farmer@example.com', 'role': 'officer'} # Admin can change role
        response = self.client.patch(detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.farmer_user.refresh_from_db()
        self.assertEqual(self.farmer_user.email, 'updated_farmer@example.com')
        self.assertEqual(self.farmer_user.role, 'officer')

    def test_farmer_can_update_own_profile(self):
        farmer_token = self._get_token('farmer', 'farmerpassword')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + farmer_token)
        detail_url = reverse('user-detail', kwargs={'pk': self.farmer_user.pk})
        data = {'first_name': 'Updated', 'last_name': 'Farmer'}
        response = self.client.patch(detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.farmer_user.refresh_from_db()
        self.assertEqual(self.farmer_user.first_name, 'Updated')
        self.assertEqual(self.farmer_user.last_name, 'Farmer')

    def test_farmer_cannot_update_other_profile(self):
        farmer_token = self._get_token('farmer', 'farmerpassword')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + farmer_token)
        detail_url = reverse('user-detail', kwargs={'pk': self.admin_user.pk})
        data = {'first_name': 'Blocked'}
        response = self.client.patch(detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_farmer_cannot_change_own_role(self):
        farmer_token = self._get_token('farmer', 'farmerpassword')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + farmer_token)
        detail_url = reverse('user-detail', kwargs={'pk': self.farmer_user.pk})
        data = {'role': 'admin'}
        response = self.client.patch(detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK) # Role field is read-only
        self.farmer_user.refresh_from_db()
        self.assertEqual(self.farmer_user.role, 'farmer') # Role should not change

    def test_admin_can_delete_any_user(self):
        admin_token = self._get_token('admin', 'adminpassword')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + admin_token)
        detail_url = reverse('user-detail', kwargs={'pk': self.farmer_user.pk})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(User.objects.count(), 2)

    def test_farmer_cannot_delete_any_user(self):
        farmer_token = self._get_token('farmer', 'farmerpassword')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + farmer_token)
        detail_url = reverse('user-detail', kwargs={'pk': self.admin_user.pk})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class CropTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(username='admin', email='admin@example.com', password='adminpassword', role='admin')
        self.farmer_user = User.objects.create_user(username='farmer', email='farmer@example.com', password='farmerpassword', role='farmer')

        self.admin_token = self._get_token('admin', 'adminpassword')
        self.farmer_token = self._get_token('farmer', 'farmerpassword')

        self.crop_list_url = reverse('crop-list')
        self.crop_data = {
            "name": "Wheat",
            "description": "Winter crop",
            "ideal_soil_type": "Loamy",
            "min_temperature_c": 10.0,
            "max_temperature_c": 25.0,
            "min_rainfall_mm_per_month": 50.0,
            "max_rainfall_mm_per_month": 100.0,
            "duration_days": 150
        }
        self.crop = Crop.objects.create(**self.crop_data)

    def _get_token(self, username, password):
        login_url = reverse('token_obtain_pair')
        response = self.client.post(login_url, {'username': username, 'password': password}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data['access']

    def test_admin_can_create_crop(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.admin_token)
        new_crop_data = {
            "name": "Rice",
            "description": "Summer crop",
            "ideal_soil_type": "Clayey",
            "min_temperature_c": 20.0,
            "max_temperature_c": 35.0,
            "min_rainfall_mm_per_month": 200.0,
            "max_rainfall_mm_per_month": 300.0,
            "duration_days": 120
        }
        response = self.client.post(self.crop_list_url, new_crop_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Crop.objects.count(), 2)

    def test_farmer_cannot_create_crop(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.farmer_token)
        new_crop_data = {
            "name": "Rice",
            "description": "Summer crop",
            "ideal_soil_type": "Clayey",
            "min_temperature_c": 20.0,
            "max_temperature_c": 35.0,
            "min_rainfall_mm_per_month": 200.0,
            "max_rainfall_mm_per_month": 300.0,
            "duration_days": 120
        }
        response = self.client.post(self.crop_list_url, new_crop_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Crop.objects.count(), 1) # Only the initial crop

    def test_any_user_can_list_crops(self):
        response = self.client.get(self.crop_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_any_user_can_retrieve_crop(self):
        detail_url = reverse('crop-detail', kwargs={'pk': self.crop.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Wheat')

    def test_admin_can_update_crop(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.admin_token)
        detail_url = reverse('crop-detail', kwargs={'pk': self.crop.pk})
        updated_data = {"description": "Updated winter crop"}
        response = self.client.patch(detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.crop.refresh_from_db()
        self.assertEqual(self.crop.description, "Updated winter crop")

    def test_farmer_cannot_update_crop(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.farmer_token)
        detail_url = reverse('crop-detail', kwargs={'pk': self.crop.pk})
        updated_data = {"description": "Attempted update"}
        response = self.client.patch(detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.crop.refresh_from_db()
        self.assertNotEqual(self.crop.description, "Attempted update")

    def test_admin_can_delete_crop(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.admin_token)
        detail_url = reverse('crop-detail', kwargs={'pk': self.crop.pk})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Crop.objects.count(), 0)

    def test_farmer_cannot_delete_crop(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.farmer_token)
        detail_url = reverse('crop-detail', kwargs={'pk': self.crop.pk})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Crop.objects.count(), 1)

