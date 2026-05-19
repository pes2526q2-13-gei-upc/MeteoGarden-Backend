import logging
from calendar import monthrange
from datetime import date, timedelta

from django.db.models import Q
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.models import Event, EventsCategory
from api.serializer import (
    EventSeedSerializer,
    EventSerializer,
)
from api.services.translate import translate_text

logger = logging.getLogger(__name__)


def translate(events, lang: str):
    with_subtitle = [e for e in events if e.subtitle and e.subtitle.strip()]

    categories_set = {e.category.name for e in events if e.category and e.category.name}
    categories_list = list(categories_set)

    titles = [e.title for e in events]
    subtitles = [e.subtitle for e in with_subtitle]

    translated_titles = translate_text(titles, lang)
    translated_subtitles = translate_text(subtitles, lang)
    translated_categories = translate_text(categories_list, lang)

    subtitles_map = {
        with_subtitle[i].id: translated_subtitles[i] for i in range(len(with_subtitle))
    }
    categories_map = {
        categories_list[i]: translated_categories[i]
        for i in range(len(categories_list))
    }

    for i, event in enumerate(events):
        event.title = translated_titles[i]

        if event.id in subtitles_map:
            event.subtitle = subtitles_map[event.id]

        if event.category and event.category.name in categories_map:
            event.category.name = categories_map[event.category.name]

    return events


def get_events_from_db(date: str, city: str | None, cat: str | None):
    full_date = parse_datetime(date) or parse_date(date)
    if not full_date:
        return []

    if hasattr(full_date, "date"):
        target_date = full_date.date()
    else:
        target_date = full_date

    filters = {
        "start_date__date__lte": target_date,
        "end_date__date__gte": target_date,
    }

    if city and city.strip():
        filters["city__iexact"] = city.strip()

    if cat and cat.strip():
        filters["category__name__iexact"] = cat.strip()

    return Event.objects.select_related("category").filter(**filters)


def get_all_events(date: str, lang: str, city: str | None, cat: str | None):
    try:
        events = get_events_from_db(date, city, cat)
        if lang not in ("ca", "CA"):
            print(lang)
            events = translate(events, lang)

        serializer = EventSerializer(events, many=True)
        return serializer.data
    except Exception as e:
        logger.exception(f"Event lookup failed: {e}")
        return []


def get_number_of_events(month: str, year: str, city: str | None, cat: str | None):
    year_int = int(year)
    month_int = int(month)

    _, last_dia = monthrange(year_int, month_int)

    first_day_month = date(year_int, month_int, 1)
    last_day_month = date(year_int, month_int, last_dia)

    filters = Q()
    if city and city.strip():
        filters &= Q(city__iexact=city.strip())
    if cat and cat.strip():
        filters &= Q(category__name__iexact=cat.strip())

    events = Event.objects.filter(
        filters, start_date__lte=last_day_month, end_date__gte=first_day_month
    )

    results = []
    actual_day = first_day_month

    while actual_day <= last_day_month:
        total_events_dia = events.filter(
            start_date__date__lte=actual_day, end_date__date__gte=actual_day
        ).count()

        results.append({"day": actual_day, "total": total_events_dia})

        actual_day += timedelta(days=1)

    return results


def get_details(event_id: str, lang: str):
    event = Event.objects.select_related("category").get(id=str(event_id))
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
    city = request.query_params.get("city")
    category = request.query_params.get("category")
    event = get_all_events(date, lang, city, category)
    return Response({"events": event})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_num_events(request):
    year = request.query_params.get("year")
    month = request.query_params.get("month")
    city = request.query_params.get("city")
    category = request.query_params.get("category")
    event = get_number_of_events(month, year, city, category)
    return Response({"events": event})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_event_detail(request):
    event_id = request.query_params.get("id")
    lang = request.query_params.get("lang")
    try:
        event = get_details(event_id, lang)
        serializer = EventSeedSerializer(event)
        return Response({"events": serializer.data})
    except Event.DoesNotExist:
        return Response({"error": "Event not found"}, status=404)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return Response({"error": "Internal server error"}, status=500)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_categories(request):
    user_lang = getattr(request.user, "language", "catalan")
    user_lang = (user_lang or "catalan").lower().strip()

    if user_lang in ("spanish", "es", "castellano", "espanyol", "español"):
        translate_lang = "es"
    elif user_lang in ("english", "en", "anglès", "angles"):
        translate_lang = "en"
    else:
        translate_lang = "ca"

    categories = list(EventsCategory.objects.all().order_by("name"))
    original_names = [category.name for category in categories]

    if translate_lang == "ca":
        display_names = original_names
    else:
        display_names = translate_text(original_names, translate_lang)

    data = [
        {
            "id": category.id,
            "name": category.name,
            "display_name": display_names[i],
        }
        for i, category in enumerate(categories)
    ]

    return Response(data)
