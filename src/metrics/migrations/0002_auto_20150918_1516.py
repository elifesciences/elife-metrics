# -*- coding: utf-8 -*-


from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='gametric',
            options={'ordering': ('date',)},
        ),
    ]
