# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0003_rename_metric_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='gametric',
            name='source',
            field=models.CharField(default=b'ga', max_length=2, choices=[(b'ga', b'Google Analytics'), (b'hw', b'Highwire')]),
        ),
        migrations.AlterField(
            model_name='gametric',
            name='period',
            field=models.CharField(max_length=10, choices=[(b'day', b'Daily'), (b'month', b'Monthly'), (b'ever', b'All time')]),
        ),
        migrations.RenameModel(
            old_name='gametric',
            new_name='metric'
        ),
    ]
