"""
Add composite index (latitude, longitude, created_at) to IoTSensorReading.

The chatbot's bounding-box query in chatbot.py filters by lat/lon range AND
orders by -created_at.  Without this index the DB must bitmap-merge the two
separate single-column indexes then filesort on created_at — O(N log N) per
chatbot request.  This composite index lets the planner satisfy the full
predicate + sort in a single index scan.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("advisory", "0010_farmer_interaction_log"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="iotsensorreading",
            index=models.Index(
                fields=["latitude", "longitude", "created_at"],
                name="iot_latlon_createdat_idx",
            ),
        ),
    ]
