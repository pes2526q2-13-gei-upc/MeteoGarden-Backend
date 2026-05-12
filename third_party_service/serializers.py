from rest_framework import serializers


class CurrentWeatherSerializer(serializers.Serializer):
    city = serializers.CharField()
    station_code = serializers.CharField()
    timestamp = serializers.DateTimeField()
    temperature = serializers.FloatField(allow_null=True)
    precipitation = serializers.FloatField(allow_null=True)
    solar_irradiance = serializers.FloatField(allow_null=True)


class DailySummarySerializer(serializers.Serializer):
    city = serializers.CharField()
    station_code = serializers.CharField()
    date = serializers.DateField()
    temperature_max = serializers.FloatField(allow_null=True)
    temperature_min = serializers.FloatField(allow_null=True)
