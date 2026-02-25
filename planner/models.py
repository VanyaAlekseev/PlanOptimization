"""
Domain models for production planning.

The schema follows the attached ER diagram:
- Project, Product, Component, TechProcess, Equipment, Personnel, ProductionPlan,
  AlgorithmComparison
- linking tables: ProductComponent, ComponentTechProcess, ProductionPlanEquipment,
  ProductionPlanPersonnel

JSONB columns are represented with Django's JSONField.
"""

from django.db import models


class Project(models.Model):
    """Project container for products, plans and algorithm comparisons."""

    name = models.CharField(max_length=255, help_text="Название проекта")
    description = models.CharField(max_length=255, blank=True, help_text="Описание проекта")
    status = models.CharField(max_length=255, db_index=True, help_text="Статус проекта")
    start_date = models.DateField(null=True, blank=True, help_text="Дата начала")
    end_date = models.DateField(null=True, blank=True, help_text="Дата окончания (факт)")
    deadline = models.DateField(null=True, blank=True, help_text="Дедлайн (план)")
    total_labor_planned = models.DecimalField(
        max_digits=19, decimal_places=0, null=True, blank=True, help_text="Плановые трудозатраты (чел.-часы)"
    )
    total_labor_actual = models.DecimalField(
        max_digits=19, decimal_places=0, null=True, blank=True, help_text="Фактические трудозатраты (чел.-часы)"
    )

    class Meta:
        db_table = "project"
        indexes = [
            models.Index(fields=["status"], name="project_status_idx"),
            models.Index(fields=["start_date"], name="project_start_dt_idx"),
            models.Index(fields=["deadline"], name="project_deadline_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.status})"


class Product(models.Model):
    """Product manufactured within a project."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="products", db_index=True)
    name = models.CharField(max_length=255, help_text="Название изделия")
    code = models.CharField(max_length=255, blank=True, db_index=True, help_text="Код/обозначение")
    type = models.CharField(max_length=255, blank=True, db_index=True, help_text="Тип изделия")
    structure_tree = models.JSONField(null=True, blank=True, help_text="Древовидная структура изделия (JSON)")
    tech_requirements = models.CharField(max_length=255, blank=True, help_text="Технические требования")
    norm_hours = models.DecimalField(
        max_digits=19, decimal_places=0, null=True, blank=True, help_text="Нормо-часы на изделие"
    )

    # From the ER diagram: PRODUCT_COMPONENT linking table exists explicitly.
    components = models.ManyToManyField(
        "Component",
        through="ProductComponent",
        related_name="products_m2m",
        blank=True,
    )

    class Meta:
        db_table = "product"
        indexes = [
            models.Index(fields=["project", "name"], name="product_proj_name_idx"),
            models.Index(fields=["project", "code"], name="product_proj_code_idx"),
            models.Index(fields=["type"], name="product_type_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name}"


class Component(models.Model):
    """Component (node) of the product structure tree."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="components_fk", db_index=True)
    parent_component = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        db_index=True,
        help_text="Родительский компонент (для иерархии)",
    )

    name = models.CharField(max_length=255, help_text="Название компонента")
    type = models.CharField(max_length=255, blank=True, db_index=True, help_text="Тип/класс компонента")
    quantity = models.IntegerField(null=True, blank=True, help_text="Количество (шт.)")
    parameters = models.JSONField(null=True, blank=True, help_text="Параметры компонента (JSON)")
    labor_per_operation = models.DecimalField(
        max_digits=19, decimal_places=0, null=True, blank=True, help_text="Трудозатраты на операцию (чел.-часы)"
    )
    dependencies = models.JSONField(
        null=True, blank=True, help_text="Технологические/структурные зависимости (JSON)"
    )

    tech_processes = models.ManyToManyField(
        "TechProcess",
        through="ComponentTechProcess",
        related_name="components",
        blank=True,
    )

    class Meta:
        db_table = "component"
        indexes = [
            models.Index(fields=["product", "name"], name="comp_prod_name_idx"),
            models.Index(fields=["product", "type"], name="comp_prod_type_idx"),
            models.Index(fields=["parent_component"], name="comp_parent_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class TechProcess(models.Model):
    """Technological process/operation associated with components."""

    name = models.CharField(max_length=255, db_index=True, help_text="Название техпроцесса/операции")
    description = models.CharField(max_length=255, blank=True, help_text="Описание")
    required_qualification = models.CharField(max_length=255, blank=True, help_text="Требуемая квалификация")
    equipment_required = models.JSONField(null=True, blank=True, help_text="Требуемое оборудование (JSON)")
    prep_time = models.IntegerField(null=True, blank=True, help_text="Подготовительное время")
    unit_time = models.IntegerField(null=True, blank=True, help_text="Штучное время")
    sequence_order = models.IntegerField(null=True, blank=True, db_index=True, help_text="Порядок выполнения")

    class Meta:
        db_table = "tech_process"
        indexes = [
            models.Index(fields=["name"], name="tp_name_idx"),
            models.Index(fields=["sequence_order"], name="tp_seq_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Equipment(models.Model):
    """Production equipment resource."""

    name = models.CharField(max_length=255, db_index=True, help_text="Название оборудования")
    type = models.CharField(max_length=255, blank=True, db_index=True, help_text="Тип оборудования")
    specifications = models.JSONField(null=True, blank=True, help_text="Характеристики (JSON)")
    work_schedule = models.JSONField(null=True, blank=True, help_text="График работы (JSON)")
    maintenance_requirements = models.CharField(max_length=255, blank=True, help_text="Требования к обслуживанию")
    cost_per_hour = models.DecimalField(
        max_digits=19, decimal_places=0, null=True, blank=True, help_text="Стоимость часа эксплуатации"
    )

    class Meta:
        db_table = "equipment"
        indexes = [
            models.Index(fields=["name"], name="equip_name_idx"),
            models.Index(fields=["type"], name="equip_type_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Personnel(models.Model):
    """Human resource (employee) used for plan calculations."""

    full_name = models.CharField(max_length=255, db_index=True, help_text="ФИО")
    position = models.CharField(max_length=255, blank=True, db_index=True, help_text="Должность")
    qualification = models.CharField(max_length=255, blank=True, help_text="Квалификация")
    specialization = models.CharField(max_length=255, blank=True, help_text="Специализация")
    work_schedule = models.JSONField(null=True, blank=True, help_text="График работы (JSON)")
    monthly_hours_norm = models.IntegerField(null=True, blank=True, help_text="Норма часов в месяц")
    current_load_percent = models.DecimalField(
        max_digits=19, decimal_places=0, null=True, blank=True, help_text="Текущая загрузка (%)"
    )

    class Meta:
        db_table = "personnel"
        indexes = [
            models.Index(fields=["full_name"], name="pers_name_idx"),
            models.Index(fields=["position"], name="pers_pos_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return self.full_name


class ProductionPlan(models.Model):
    """Calculated manufacturing plan for a project (per chosen algorithm)."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="production_plans", db_index=True)
    algorithm_used = models.CharField(max_length=255, db_index=True, help_text="Используемый алгоритм")
    created_date = models.DateField(null=True, blank=True, help_text="Дата создания")
    status = models.CharField(max_length=255, db_index=True, help_text="Статус плана")
    schedule = models.JSONField(null=True, blank=True, help_text="Расписание (JSON)")
    actual_data = models.JSONField(null=True, blank=True, help_text="Фактические данные (JSON)")
    deviations = models.JSONField(null=True, blank=True, help_text="Отклонения (JSON)")

    equipment = models.ManyToManyField(
        Equipment,
        through="ProductionPlanEquipment",
        related_name="production_plans",
        blank=True,
    )
    personnel = models.ManyToManyField(
        Personnel,
        through="ProductionPlanPersonnel",
        related_name="production_plans",
        blank=True,
    )

    class Meta:
        db_table = "production_plan"
        indexes = [
            models.Index(fields=["project", "status"], name="plan_proj_status_idx"),
            models.Index(fields=["project", "created_date"], name="plan_proj_created_idx"),
            models.Index(fields=["algorithm_used"], name="plan_algo_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Plan #{self.pk} ({self.algorithm_used})"


class AlgorithmComparison(models.Model):
    """Aggregated metrics for comparing planning algorithms within a project."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="algorithm_comparisons", db_index=True)
    algorithm_name = models.CharField(max_length=255, db_index=True, help_text="Название алгоритма")
    total_duration = models.FloatField(null=True, blank=True, help_text="Общая длительность (критерий)")
    resource_utilization = models.FloatField(null=True, blank=True, help_text="Утилизация ресурсов (критерий)")
    deadline_satisfaction = models.FloatField(null=True, blank=True, help_text="Удовлетворение дедлайна (критерий)")
    computed_date = models.DateField(null=True, blank=True, help_text="Дата расчета")

    class Meta:
        db_table = "algorithm_comparison"
        indexes = [
            models.Index(fields=["project", "algorithm_name"], name="algo_proj_name_idx"),
            models.Index(fields=["computed_date"], name="algo_comp_dt_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.algorithm_name} ({self.project_id})"


class ProductComponent(models.Model):
    """Linking table PRODUCT_COMPONENT (Product <-> Component)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_index=True)
    component = models.ForeignKey(Component, on_delete=models.CASCADE, db_index=True)

    class Meta:
        db_table = "product_component"
        constraints = [
            models.UniqueConstraint(fields=["product", "component"], name="uq_product_component"),
        ]
        indexes = [
            models.Index(fields=["product"], name="pc_product_idx"),
            models.Index(fields=["component"], name="pc_component_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.product_id} - {self.component_id}"


class ComponentTechProcess(models.Model):
    """Linking table COMPONENT_TECH_PROCESS (Component <-> TechProcess)."""

    component = models.ForeignKey(Component, on_delete=models.CASCADE, db_index=True)
    tech_process = models.ForeignKey(TechProcess, on_delete=models.CASCADE, db_index=True)

    class Meta:
        db_table = "component_tech_process"
        constraints = [
            models.UniqueConstraint(fields=["component", "tech_process"], name="uq_component_tech_process"),
        ]
        indexes = [
            models.Index(fields=["component"], name="ctp_component_idx"),
            models.Index(fields=["tech_process"], name="ctp_techproc_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.component_id} - {self.tech_process_id}"


class ProductionPlanEquipment(models.Model):
    """Linking table PRODUCTION_PLAN_EQUIPMENT (ProductionPlan <-> Equipment)."""

    production_plan = models.ForeignKey(ProductionPlan, on_delete=models.CASCADE, db_index=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, db_index=True)
    hours_required = models.IntegerField(null=True, blank=True, help_text="Требуемые часы")

    class Meta:
        db_table = "production_plan_equipment"
        constraints = [
            models.UniqueConstraint(fields=["production_plan", "equipment"], name="uq_plan_equipment"),
        ]
        indexes = [
            models.Index(fields=["production_plan"], name="ppe_plan_idx"),
            models.Index(fields=["equipment"], name="ppe_equipment_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.production_plan_id} - {self.equipment_id}"


class ProductionPlanPersonnel(models.Model):
    """Linking table PRODUCTION_PLAN_PERSONNEL (ProductionPlan <-> Personnel)."""

    production_plan = models.ForeignKey(ProductionPlan, on_delete=models.CASCADE, db_index=True)
    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE, db_index=True)
    hours_assigned = models.IntegerField(null=True, blank=True, help_text="Назначенные часы")

    class Meta:
        db_table = "production_plan_personnel"
        constraints = [
            models.UniqueConstraint(fields=["production_plan", "personnel"], name="uq_plan_personnel"),
        ]
        indexes = [
            models.Index(fields=["production_plan"], name="ppp_plan_idx"),
            models.Index(fields=["personnel"], name="ppp_personnel_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.production_plan_id} - {self.personnel_id}"
