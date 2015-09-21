# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0005_auto_20150921_1541'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='metric',
            unique_together=set([('article', 'date', 'period', 'source')]),
        ),
    ]
