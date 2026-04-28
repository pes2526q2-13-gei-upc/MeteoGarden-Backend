from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.models import Event
from api.serializer import EventSeedSerializer, EventSerializer
from api.views.views_translate import translate_text


def getAllEventsByCity(date: str, city: str, lang: str):
    full_date = parse_datetime(date) or parse_date(date)
    if not full_date:
        return []

    if hasattr(full_date, "date"):
        target_date = full_date.date()
    else:
        target_date = full_date
    try:
        events = Event.objects.filter(
            start_date__date__lte=target_date,
            end_date__date__gte=target_date,
            city__iexact=city,
        )
        with_subtitle = [e for e in events if e.subtitle and e.subtitle.strip]

        titles = [e.title for e in events]
        subtitles = [e.subtitle for e in with_subtitle]
        translated_titles = translate_text(titles, lang)
        translated_subtitles = translate_text(subtitles, lang)
        subtitles_map = {
            with_subtitle[i].id: translated_subtitles[i]
            for i in range(len(with_subtitle))
        }
        for i, event in enumerate(events):
            event.title = translated_titles[i]
            if event.id in subtitles_map:
                event.subtitle = subtitles_map[event.id]

        serializer = EventSerializer(events, many=True)
        return serializer.data
    except Exception as e:
        return {"error": str(e)}


def getAllEvents(date: str, lang: str):
    full_date = parse_datetime(date) or parse_date(date)
    if not full_date:
        return []

    if hasattr(full_date, "date"):
        target_date = full_date.date()
    else:
        target_date = full_date
    try:
        events = Event.objects.filter(
            start_date__date__lte=target_date, end_date__date__gte=target_date
        )
        with_subtitle = [e for e in events if e.subtitle and e.subtitle.strip]

        titles = [e.title for e in events]
        subtitles = [e.subtitle for e in with_subtitle]
        translated_titles = translate_text(titles, lang)
        translated_subtitles = translate_text(subtitles, lang)
        subtitles_map = {
            with_subtitle[i].id: translated_subtitles[i]
            for i in range(len(with_subtitle))
        }
        for i, event in enumerate(events):
            event.title = translated_titles[i]
            if event.id in subtitles_map:
                event.subtitle = subtitles_map[event.id]

        serializer = EventSerializer(events, many=True)
        return serializer.data
    except Exception as e:
        return {"error": str(e)}


def getAllEventsByCategory(date: str, lang: str, cat: str):
    full_date = parse_datetime(date) or parse_date(date)
    if not full_date:
        return []

    if hasattr(full_date, "date"):
        target_date = full_date.date()
    else:
        target_date = full_date
    try:
        events = Event.objects.filter(
            start_date__date__lte=target_date,
            end_date__date__gte=target_date,
            category__iexact=cat,
        )
        with_subtitle = [e for e in events if e.subtitle and e.subtitle.strip]

        titles = [e.title for e in events]
        subtitles = [e.subtitle for e in with_subtitle]
        translated_titles = translate_text(titles, lang)
        translated_subtitles = translate_text(subtitles, lang)
        subtitles_map = {
            with_subtitle[i].id: translated_subtitles[i]
            for i in range(len(with_subtitle))
        }
        for i, event in enumerate(events):
            event.title = translated_titles[i]
            if event.id in subtitles_map:
                event.subtitle = subtitles_map[event.id]

        serializer = EventSerializer(events, many=True)
        return serializer.data
    except Exception as e:
        return {"error": str(e)}


def getNumberOfEvents(month: str, year: str):
    events = (
        Event.objects.filter(start_date__year=year, start_date__month=month)
        .annotate(day=TruncDay("start_date"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    return events


def getDetails(id: str, lang: str):
    event = Event.objects.get(id=id)
    if lang not in ("cat", "CAT"):
        field_to_translate = ["title", "description", "category"]
        if getattr(event, "subtitle", None):
            field_to_translate.append("subtitle")
        if getattr(event, "tags", None):
            field_to_translate.append("tags")

        to_translate = [getattr(event, field) for field in field_to_translate]

        translated_event = translate_text(to_translate, lang)

        for i, field in enumerate(field_to_translate):
            setattr(event, field, translated_event[i])

    return event


@api_view(["GET"])
@permission_classes([AllowAny])
def getEvents(request):
    date = request.query_params.get("date")
    lang = request.query_params.get("lang")
    event = getAllEvents(date, lang)
    return Response({"events": event})


@api_view(["GET"])
@permission_classes([AllowAny])
def getEventsByCity(request):
    date = request.query_params.get("date")
    lang = request.query_params.get("lang")
    city = request.query_params.get("city")
    event = getAllEventsByCity(date, city, lang)
    return Response({"events": event})


@api_view(["GET"])
@permission_classes([AllowAny])
def getEventsByCategory(request):
    date = request.query_params.get("date")
    lang = request.query_params.get("lang")
    category = request.query_params.get("category")
    event = getAllEventsByCategory(date, lang, category)
    return Response({"events": event})


@api_view(["GET"])
@permission_classes([AllowAny])
def getNumEvents(request):
    year = request.query_params.get("year")
    month = request.query_params.get("month")
    event = getNumberOfEvents(month, year)
    return Response({"events": event})


@api_view(["GET"])
@permission_classes([AllowAny])
def getEventDetail(request):
    id = request.query_params.get("id")
    lang = request.query_params.get("lang")
    event = getDetails(id, lang)
    serializer = EventSeedSerializer(event)
    return Response({"events": serializer.data})
