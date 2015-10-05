# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        ('janeus', '0002_janeusrole'),
    ]

    operations = [
        migrations.AddField(
            model_name='janeusrole',
            name='sites',
            field=models.ManyToManyField(to='sites.Site', blank=True),
            preserve_default=True,
        ),
    ]
