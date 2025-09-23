from django.db import models

# Create your models here.

class CropAdvisory(models.Model):
    crop_type = models.CharField(max_length=100)
    soil_type = models.CharField(max_length=100)
    weather_condition = models.CharField(max_length=100)
    recommendation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop_type} - {self.soil_type}"