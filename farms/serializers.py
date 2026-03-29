from rest_framework import serializers

from production.models import FarmProductionModel
from .models import FarmModel
from django.contrib.auth import get_user_model
from django.utils import timezone
from farm_trays.models import FarmTrayModel
from farm_sessions.models import FarmSessionModel
from trays.models import SessionTrayModel, TrayStepModel
from announcements.models import AnnouncementModel
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from datetime import date, timedelta

User = get_user_model()

class FarmSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.id')
    owner_name = serializers.ReadOnlyField(source='owner.username')
    members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        required=False
    )
    blocked = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        required=False
    )
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = FarmModel
        fields = [
            'id',
            'name',
            'description',
            'image_url',
            'password',
            'owner',
            'owner_name',
            'members',
            'blocked',
        ]
    
    def create(self, validated_data):
        user = self.context['request'].user
        members = validated_data.pop('members', [])
        farm = FarmModel.objects.create(owner=user, **validated_data)
    
        farm.members.add(user, *members)
        return farm

class JoinFarmSerializer(serializers.Serializer):
    farm_id = serializers.IntegerField()
    password = serializers.CharField()    
    
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'username', 'email', 'profile_picture']

class FarmDashboardSerializer(serializers.ModelSerializer):
    tray_count = serializers.SerializerMethodField()
    announcement_count = serializers.SerializerMethodField()
    session_trays_count_by_day = serializers.SerializerMethodField()
    detected_and_reject_by_day = serializers.SerializerMethodField()
    recent_harvested_trays = serializers.SerializerMethodField()
    production_by_day = serializers.SerializerMethodField()
    production_summary = serializers.SerializerMethodField()

    class Meta:
        model = FarmModel
        fields = [
            'id', 'name', 'description', 'image_url',
            'session_trays_count_by_day', 'tray_count',
            'announcement_count', 'detected_and_reject_by_day',
            'recent_harvested_trays', 'production_by_day', 'production_summary'
        ]

    def _date_filter(self):
        request = self.context.get('request')
        date_from = request.query_params.get('from') if request else None
        date_to = request.query_params.get('to') if request else None
        if date_from and date_to:
            return date_from, date_to
        today = date.today()
        return None, None

    def get_tray_count(self, obj):
        return FarmTrayModel.objects.filter(farm=obj).count()

    def get_announcement_count(self, obj):
        return AnnouncementModel.objects.filter(farm=obj).count()

    def get_session_trays_count_by_day(self, obj):
        date_from, date_to = self._date_filter()
        qs = SessionTrayModel.objects.filter(tray__farm=obj, finished_at__isnull=False)
        if date_from and date_to:
            qs = qs.filter(finished_at__date__gte=date_from, finished_at__date__lte=date_to)
        session_trays = (
            qs.annotate(day=TruncDate('finished_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        return [{'finished_at': t['day'], 'count': t['count']} for t in session_trays]

    def get_detected_and_reject_by_day(self, obj):
        date_from, date_to = self._date_filter()
        qs = SessionTrayModel.objects.filter(tray__farm=obj, created_at__isnull=False)
        if date_from and date_to:
            qs = qs.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        daily_stats = (
            qs.annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(total_detected=Sum('steps__detected'), total_rejects=Sum('steps__rejects'))
            .order_by('day')
        )
        return [{'day': s['day'], 'detected': s['total_detected'] or 0, 'rejects': s['total_rejects'] or 0} for s in daily_stats]

    def get_production_by_day(self, obj):
        date_from, date_to = self._date_filter()
        qs = FarmProductionModel.objects.filter(farm=obj)
        if date_from and date_to:
            qs = qs.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        rows = (
            qs.annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(total_quantity=Sum('quantity'), total_sales=Sum('total'))
            .order_by('day')
        )
        return [{'day': r['day'], 'quantity': float(r['total_quantity'] or 0), 'sales': r['total_sales'] or 0} for r in rows]

    def get_production_summary(self, obj):
        date_from, date_to = self._date_filter()
        qs = FarmProductionModel.objects.filter(farm=obj)
        if date_from and date_to:
            qs = qs.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        result = qs.aggregate(total_quantity=Sum('quantity'), total_sales=Sum('total'))
        return {
            'total_quantity': float(result['total_quantity'] or 0),
            'total_sales': result['total_sales'] or 0,
        }
        
    def get_recent_harvested_trays(self, obj):
        trays = (
            SessionTrayModel.objects
            .filter(tray__farm=obj, finished_at__isnull=False)
            .order_by('-finished_at')[:3]
        )
        return [{'id': t.id, 'finished_at': t.finished_at, 'created_at': t.created_at,
                 'tray_name': t.tray.name if t.tray else None, 'tray_id': t.tray.id if t.tray else None}
                for t in trays]
    
