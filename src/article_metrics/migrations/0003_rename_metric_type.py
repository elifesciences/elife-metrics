# -*- coding: utf-8 -*-


from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0002_auto_20150918_1516'),
    ]

    operations = [
        migrations.RenameField(
            model_name='GAMetric',
            old_name='type',
            new_name='period'
        ),
    ]
