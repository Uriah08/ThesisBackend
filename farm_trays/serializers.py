from rest_framework import serializers
from .models import FarmTrayModel
from trays.models import SessionTrayModel
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate

class FarmTraySerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source="farm.name", read_only=True)
    farm_owner = serializers.IntegerField(source="farm.owner.id", read_only=True)
    
    latest_session_datetime = serializers.DateTimeField(read_only=True)

    class Meta:
        model = FarmTrayModel
        fields = ["id", "farm", "farm_name", "farm_owner", "name", "description", "status", "created_at", "latest_session_datetime",]
        read_only_fields = ["status", "created_at"]

class TrayDashboardSerializer(serializers.ModelSerializer):
    session_tray_count = serializers.SerializerMethodField()
    detected_and_reject_by_day = serializers.SerializerMethodField()
    recent_harvested_trays = serializers.SerializerMethodField()
    detection_summary = serializers.SerializerMethodField()

    class Meta:
        model = FarmTrayModel
        fields = [
            "id", "name", "status", "created_at",
            "session_tray_count", "detected_and_reject_by_day",
            "recent_harvested_trays", "detection_summary",
        ]

    def _date_filter(self):
        request = self.context.get('request')
        date_from = request.query_params.get('from') if request else None
        date_to = request.query_params.get('to') if request else None
        if date_from and date_to:
            return date_from, date_to
        return None, None

    def get_session_tray_count(self, obj):
        date_from, date_to = self._date_filter()
        qs = SessionTrayModel.objects.filter(tray=obj, finished_at__isnull=False)
        if date_from and date_to:
            qs = qs.filter(finished_at__date__gte=date_from, finished_at__date__lte=date_to)
        session_trays = (
            qs.annotate(day=TruncDate('finished_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        return [{"finished_at": t["day"], "count": t["count"]} for t in session_trays]

    def get_detected_and_reject_by_day(self, obj):
        date_from, date_to = self._date_filter()
        qs = SessionTrayModel.objects.filter(tray=obj, created_at__isnull=False)
        if date_from and date_to:
            qs = qs.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        daily_stats = (
            qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total_detected=Sum("steps__detected"), total_rejects=Sum("steps__rejects"))
            .order_by("day")
        )
        return [{"day": s["day"], "detected": s["total_detected"] or 0, "rejects": s["total_rejects"] or 0} for s in daily_stats]

    def get_detection_summary(self, obj):
        date_from, date_to = self._date_filter()
        qs = SessionTrayModel.objects.filter(tray=obj)
        if date_from and date_to:
            qs = qs.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        result = qs.aggregate(total_detected=Sum("steps__detected"), total_rejects=Sum("steps__rejects"))
        total_detected = result["total_detected"] or 0
        total_rejects = result["total_rejects"] or 0
        total = total_detected + total_rejects
        reject_rate = round((total_rejects / total) * 100, 1) if total > 0 else 0
        return {
            "total_detected": total_detected,
            "total_rejects": total_rejects,
            "reject_rate": reject_rate,
        }

    def get_recent_harvested_trays(self, obj):
        trays = (
            SessionTrayModel.objects
            .filter(tray=obj, finished_at__isnull=False)
            .order_by("-finished_at")[:3]
        )
        return [{"id": t.id, "finished_at": t.finished_at, "created_at": t.created_at,
                 "tray_name": t.tray.name if t.tray else None, "tray_id": t.tray.id if t.tray else None}
                for t in trays]