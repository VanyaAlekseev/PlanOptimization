from __future__ import annotations

from rest_framework import serializers

from planner.models import (
    AlgorithmComparison,
    Component,
    ComponentTechProcess,
    Equipment,
    Personnel,
    Product,
    ProductionPlan,
    ProductionPlanEquipment,
    ProductionPlanPersonnel,
    Project,
    TechProcess,
)


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class TechProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechProcess
        fields = "__all__"


class ComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = "__all__"


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = "__all__"


class PersonnelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personnel
        fields = "__all__"


class ProductionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionPlan
        fields = "__all__"


class AlgorithmComparisonSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlgorithmComparison
        fields = "__all__"


class ProductImportStubSerializer(serializers.Serializer):
    """
    Stub payload for CAD import (currently JSON).
    """

    payload = serializers.JSONField()


class OptimizationRequestSerializer(serializers.Serializer):
    algorithm = serializers.ChoiceField(choices=["cpm", "ga", "sa"])
    async_run = serializers.BooleanField(required=False, default=False)
    params = serializers.JSONField(required=False, default=dict)


class CompareAlgorithmsRequestSerializer(serializers.Serializer):
    async_run = serializers.BooleanField(required=False, default=False)
    params = serializers.JSONField(required=False, default=dict)


class ResourceAvailabilitySerializer(serializers.Serializer):
    resource_type = serializers.ChoiceField(choices=["equipment", "personnel"])
    resource_id = serializers.IntegerField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()

