# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0006_auto_20150921_1545'),
    ]

    operations = [
        migrations.AlterField(
            model_name='metric',
            name='abstract',
            field=models.PositiveIntegerField(help_text=b'article abstract page views'),
        ),
        migrations.AlterField(
            model_name='metric',
            name='digest',
            field=models.PositiveIntegerField(help_text=b'article digest page views'),
        ),
        migrations.AlterField(
            model_name='metric',
            name='full',
            field=models.PositiveIntegerField(help_text=b'article page views'),
        ),
        migrations.AlterField(
            model_name='metric',
            name='pdf',
            field=models.PositiveIntegerField(help_text=b'pdf downloads'),
        ),
    ]
