from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Iterable, Optional, Type, TypeVar

from django.db import models, transaction


TModel = TypeVar("TModel", bound=models.Model)


@dataclass(frozen=True)
class BaseRepository(Generic[TModel]):
    """
    Base repository that encapsulates CRUD for a single model.

    Concrete repositories can override/extend behavior and add query methods.
    """

    model: Type[TModel]

    def get_by_id(self, obj_id: int) -> Optional[TModel]:
        return self.model.objects.filter(pk=obj_id).first()

    def list(self, *, filters: Optional[dict[str, Any]] = None) -> models.QuerySet[TModel]:
        qs = self.model.objects.all()
        return qs.filter(**filters) if filters else qs

    @transaction.atomic
    def create(self, **data: Any) -> TModel:
        return self.model.objects.create(**data)

    @transaction.atomic
    def update(self, obj: TModel, **data: Any) -> TModel:
        for key, value in data.items():
            setattr(obj, key, value)
        obj.full_clean()
        obj.save(update_fields=list(data.keys()) if data else None)
        return obj

    @transaction.atomic
    def delete(self, obj: TModel) -> None:
        obj.delete()

    def bulk_create(self, objs: Iterable[TModel], *, batch_size: int = 1000) -> list[TModel]:
        return self.model.objects.bulk_create(list(objs), batch_size=batch_size)

