from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from planner.api.viewsets import (
    AlgorithmComparisonViewSet,
    ComponentViewSet,
    PlanningViewSet,
    ProductViewSet,
    ProductionPlanViewSet,
    ProjectViewSet,
    ReportViewSet,
    ResourceViewSet,
    TechProcessViewSet,
)


router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="projects")
router.register(r"products", ProductViewSet, basename="products")
router.register(r"components", ComponentViewSet, basename="components")
router.register(r"tech-processes", TechProcessViewSet, basename="tech-processes")
router.register(r"plans", ProductionPlanViewSet, basename="plans")
router.register(r"algorithm-comparisons", AlgorithmComparisonViewSet, basename="algorithm-comparisons")
router.register(r"planning", PlanningViewSet, basename="planning")
router.register(r"resources", ResourceViewSet, basename="resources")
router.register(r"reports", ReportViewSet, basename="reports")


urlpatterns = [
    path("", include(router.urls)),
]

