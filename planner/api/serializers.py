from __future__ import annotations

from decimal import Decimal

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
from planner.repositories.equipment import EquipmentRepository
from planner.repositories.personnel import PersonnelRepository
from planner.repositories.project import ProjectRepository
from planner.services.project_management_service import ProjectManagementService


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        if request is None or request.method != "POST":
            return attrs

        required_hours = Decimal(str(attrs.get("total_labor_planned") or 0))
        if required_hours <= 0:
            return attrs

        svc = ProjectManagementService(
            project_repo=ProjectRepository(),
            equipment_repo=EquipmentRepository(),
            personnel_repo=PersonnelRepository(),
        )
        try:
            svc.validate_resource_capacity_for_project(
                required_hours=required_hours,
                start_date=attrs.get("start_date"),
                deadline=attrs.get("deadline"),
            )
        except ValueError as exc:
            raise serializers.ValidationError({"resources": str(exc)}) from exc

        return attrs


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
    params = serializers.DictField(required=False, default=dict)

    def validate_params(self, value):
        # Управляемые параметры оптимизации (прочие поля не запрещаем для обратной совместимости).
        if "alpha" in value:
            value["alpha"] = float(value["alpha"])
        if "beta" in value:
            value["beta"] = float(value["beta"])
        if "gamma" in value:
            value["gamma"] = float(value["gamma"])
        if "use_work_schedule" in value:
            value["use_work_schedule"] = bool(value["use_work_schedule"])
        if "strict_missing_resources" in value:
            value["strict_missing_resources"] = bool(value["strict_missing_resources"])
        return value


class CompareAlgorithmsRequestSerializer(serializers.Serializer):
    async_run = serializers.BooleanField(required=False, default=False)
    params = serializers.DictField(required=False, default=dict)

    def validate_params(self, value):
        if "alpha" in value:
            value["alpha"] = float(value["alpha"])
        if "beta" in value:
            value["beta"] = float(value["beta"])
        if "gamma" in value:
            value["gamma"] = float(value["gamma"])
        if "use_work_schedule" in value:
            value["use_work_schedule"] = bool(value["use_work_schedule"])
        if "strict_missing_resources" in value:
            value["strict_missing_resources"] = bool(value["strict_missing_resources"])
        return value


class ResourceAvailabilitySerializer(serializers.Serializer):
    resource_type = serializers.ChoiceField(choices=["equipment", "personnel"])
    resource_id = serializers.IntegerField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()

