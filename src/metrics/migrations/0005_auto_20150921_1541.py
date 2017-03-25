# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0004_auto_20150921_1014'),
    ]

    operations = [
        migrations.AlterField(
            model_name='metric',
            name='source',
            field=models.CharField(max_length=2, choices=[(b'ga', b'Google Analytics'), (b'hw', b'Highwire')]),
        ),
    ]
