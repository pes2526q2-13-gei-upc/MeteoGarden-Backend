from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.models import Event, EventsCategory
from api.serializer import (
    EventsCategorySerializer,
    EventSeedSerializer,
    EventSerializer,
)
from api.views.views_translate import translate_text


def translate(events, lang: str):
    with_subtitle = [e for e in events if e.subtitle and e.subtitle.strip]

    titles = [e.title for e in events]
    subtitles = [e.subtitle for e in with_subtitle]
    translated_titles = translate_text(titles, lang)
    translated_subtitles = translate_text(subtitles, lang)
    subtitles_map = {
        with_subtitle[i].id: translated_subtitles[i] for i in range(len(with_subtitle))
    }
    for i, event in enumerate(events):
        event.title = translated_titles[i]
        if event.id in subtitles_map:
            event.subtitle = subtitles_map[event.id]

    return events


def get_all_events_by_city(date: str, city: str, lang: str):
    full_date = parse_datetime(date) or parse_date(date)
    if not full_date:
        return []

    if hasattr(full_date, "date"):
        target_date = full_date.date()
    else:
        target_date = full_date
    try:
        events = Event.objects.selected_related("category").filter(
            start_date__date__lte=target_date,
            end_date__date__gte=target_date,
            city__iexact=city,
        )
        events = translate(events, lang)

        serializer = EventSerializer(events, many=True)
        return serializer.data
    except Exception as e:
        return {"error": str(e)}


def get_all_events(date: str, lang: str):
    full_date = parse_datetime(date) or parse_date(date)
    if not full_date:
        return []

    if hasattr(full_date, "date"):
        target_date = full_date.date()
    else:
        target_date = full_date
    try:
        events = Event.objects.select_related("category").filter(
            start_date__date__lte=target_date, end_date__date__gte=target_date
        )

        events = translate(events, lang)
        serializer = EventSerializer(events, many=True)
        return serializer.data
    except Exception as e:
        return {"error": str(e)}


def get_all_events_by_category(date: str, lang: str, cat: str):
    full_date = parse_datetime(date) or parse_date(date)
    if not full_date:
        return []

    if hasattr(full_date, "date"):
        target_date = full_date.date()
    else:
        target_date = full_date
    try:
        events = Event.objects.select_related("category").filter(
            start_date__date__lte=target_date,
            end_date__date__gte=target_date,
            category__name__iexact=cat,
        )
        events = translate(events, lang)

        serializer = EventSerializer(events, many=True)
        return serializer.data
    except Exception as e:
        return {"error": str(e)}


def get_number_of_events(month: str, year: str, city: str | None):
    if city is None:
        events = (
            Event.objects.filter(start_date__year=year, start_date__month=month)
            .annotate(day=TruncDay("start_date"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )
    else:
        events = (
            Event.objects.filter(
                start_date__year=year, start_date__month=month, city__iexact=city
            )
            .annotate(day=TruncDay("start_date"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )

    return events


def get_details(event_id: str, lang: str):
    event = Event.objects.select_related("category").get(id=event_id)
    if lang not in ("cat", "CAT"):
        field_to_translate = ["title", "description"]
        if getattr(event, "subtitle", None):
            field_to_translate.append("subtitle")
        if getattr(event, "tags", None):
            field_to_translate.append("tags")

        to_translate = [getattr(event, field) for field in field_to_translate]
        if event.category:
            to_translate.append(event.category.name)

        translated_event = translate_text(to_translate, lang)

        for i, field in enumerate(field_to_translate):
            setattr(event, field, translated_event[i])

        if event.category:
            event.category.name = translated_event[-1]

    return event


@api_view(["GET"])
@permission_classes([AllowAny])
def get_events(request):
    date = request.query_params.get("date")
    lang = request.query_params.get("lang")
    event = get_all_events(date, lang)
    return Response({"events": event})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_events_by_city(request):
    date = request.query_params.get("date")
    lang = request.query_params.get("lang")
    city = request.query_params.get("city")
    event = get_all_events_by_city(date, city, lang)
    return Response({"events": event})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_events_by_category(request):
    date = request.query_params.get("date")
    lang = request.query_params.get("lang")
    category = request.query_params.get("category")
    event = get_all_events_by_category(date, lang, category)
    return Response({"events": event})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_num_events(request):
    year = request.query_params.get("year")
    month = request.query_params.get("month")
    city = request.query_params.get("city")
    event = get_number_of_events(month, year, city)
    return Response({"events": event})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_event_detail(request):
    event_id = request.query_params.get("id")
    lang = request.query_params.get("lang")
    event = get_details(event_id, lang)
    serializer = EventSeedSerializer(event)
    return Response({"events": serializer.data})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_categories(request):
    categories = EventsCategory.objects.all()
    serializer = EventsCategorySerializer(categories, many=True)
    return Response(serializer.data)
