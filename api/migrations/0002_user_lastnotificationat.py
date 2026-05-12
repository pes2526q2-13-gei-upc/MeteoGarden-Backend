from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE api_plantingarden
                DROP COLUMN IF EXISTS "lastNotificationAt";
            """,
            reverse_sql="""
                ALTER TABLE api_plantingarden
                ADD COLUMN "lastNotificationAt" timestamp with time zone NULL;
            """,
        ),
        migrations.AddField(
            model_name="user",
            name="lastNotificationAt",
            field=models.DateTimeField(
                null=True,
                blank=True,
            ),
        ),
    ]
