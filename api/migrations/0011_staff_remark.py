# Generated by Django 2.1.7 on 2019-03-27 13:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_auto_20190327_0937'),
    ]

    operations = [
        migrations.AddField(
            model_name='staff',
            name='remark',
            field=models.CharField(max_length=64, null=True),
        ),
    ]
