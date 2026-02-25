from django.contrib import admin

from . import models


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "start_date", "deadline", "end_date")
    search_fields = ("name", "description")
    list_filter = ("status",)


@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "type", "project")
    search_fields = ("name", "code")
    list_filter = ("type", "project")


@admin.register(models.Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "product", "parent_component", "quantity")
    search_fields = ("name",)
    list_filter = ("type", "product")
    raw_id_fields = ("product", "parent_component")


@admin.register(models.TechProcess)
class TechProcessAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "sequence_order", "prep_time", "unit_time")
    search_fields = ("name", "description", "required_qualification")
    list_filter = ("sequence_order",)


@admin.register(models.Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "cost_per_hour")
    search_fields = ("name",)
    list_filter = ("type",)


@admin.register(models.Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "position", "monthly_hours_norm", "current_load_percent")
    search_fields = ("full_name", "position", "qualification", "specialization")
    list_filter = ("position",)


@admin.register(models.ProductionPlan)
class ProductionPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "algorithm_used", "status", "created_date")
    search_fields = ("algorithm_used",)
    list_filter = ("status", "algorithm_used", "project")
    raw_id_fields = ("project",)


@admin.register(models.AlgorithmComparison)
class AlgorithmComparisonAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "project",
        "algorithm_name",
        "total_duration",
        "resource_utilization",
        "deadline_satisfaction",
        "computed_date",
    )
    search_fields = ("algorithm_name",)
    list_filter = ("algorithm_name", "project")


@admin.register(models.ProductComponent)
class ProductComponentAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "component")
    raw_id_fields = ("product", "component")


@admin.register(models.ComponentTechProcess)
class ComponentTechProcessAdmin(admin.ModelAdmin):
    list_display = ("id", "component", "tech_process")
    raw_id_fields = ("component", "tech_process")


@admin.register(models.ProductionPlanEquipment)
class ProductionPlanEquipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "production_plan", "equipment", "hours_required")
    raw_id_fields = ("production_plan", "equipment")


@admin.register(models.ProductionPlanPersonnel)
class ProductionPlanPersonnelAdmin(admin.ModelAdmin):
    list_display = ("id", "production_plan", "personnel", "hours_assigned")
    raw_id_fields = ("production_plan", "personnel")
