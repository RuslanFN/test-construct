"""In-memory эмулятор async-коллекций pymongo для тестов.

Реализует только тот подмножеств API, которое использует приложение:
find/find_one (с сортировкой, проекцией, $in, $or, $regex), insert_one,
update_one/update_many ($set), delete_one/delete_many, replace_one,
find_one_and_update, aggregate ($group/$sum), create_index.

Данные хранятся в памяти процесса, изолированно для каждого теста
(создаётся новый экземпляр FakeDB в фикстуре).
"""
from __future__ import annotations

import copy
import re
import uuid
from datetime import datetime


def _match_value(doc_value, cond):
    """Сравнение значения поля с условием (скаляр или оператор)."""
    if isinstance(cond, dict) and any(k.startswith('$') for k in cond):
        for op, arg in cond.items():
            if op == '$options':
                continue  # опции regex обрабатываются в $regex
            if op == '$in':
                if doc_value not in arg:
                    return False
            elif op == '$nin':
                if doc_value in arg:
                    return False
            elif op == '$regex':
                flags = 0
                if cond.get('$options') and 'i' in cond['$options']:
                    flags |= re.IGNORECASE
                if doc_value is None or not re.search(arg, str(doc_value), flags):
                    return False
            elif op == '$eq':
                if doc_value != arg:
                    return False
            elif op == '$ne':
                if doc_value == arg:
                    return False
            elif op in ('$lt', '$lte', '$gt', '$gte'):
                # Сравнение (в т.ч. datetime) — используется очисткой по retention.
                if doc_value is None:
                    return False
                try:
                    if op == '$lt' and not (doc_value < arg):
                        return False
                    if op == '$lte' and not (doc_value <= arg):
                        return False
                    if op == '$gt' and not (doc_value > arg):
                        return False
                    if op == '$gte' and not (doc_value >= arg):
                        return False
                except TypeError:
                    return False
            else:  # неизвестный оператор — считаем несовпадением
                return False
        return True
    return doc_value == cond


def _match(doc: dict, query: dict) -> bool:
    for key, cond in query.items():
        if key == '$or':
            if not any(_match(doc, sub) for sub in cond):
                return False
            continue
        if key == '$and':
            if not all(_match(doc, sub) for sub in cond):
                return False
            continue
        # поддержка вложенных полей "a.b"
        value = doc
        for part in key.split('.'):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                value = None
                break
        if not _match_value(value, cond):
            return False
    return True


def _apply_set(doc: dict, updates: dict) -> None:
    if '$set' in updates:
        for k, v in updates['$set'].items():
            parts = k.split('.')
            target = doc
            for p in parts[:-1]:
                target = target.setdefault(p, {})
            target[parts[-1]] = v
    # прочие операторы ($unset и т.п.) приложением не используются


class AsyncCursor:
    def __init__(self, docs: list[dict]):
        self._docs = docs
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i >= len(self._docs):
            raise StopAsyncIteration
        d = self._docs[self._i]
        self._i += 1
        return d

    def sort(self, key: str, direction: int = 1):
        reverse = direction == -1

        def sort_key(d):
            v = d
            for part in key.split('.'):
                v = v.get(part) if isinstance(v, dict) else None
            # None безопасно: приводим к строке-минимуму
            return (v is not None, v if v is not None else '')

        self._docs.sort(key=sort_key, reverse=reverse)
        return self

    async def to_list(self, length=None):
        return self._docs[:length] if length else list(self._docs)


class FakeCollection:
    def __init__(self):
        self._docs: list[dict] = []

    # --- запись ---
    async def insert_one(self, doc: dict):
        self._docs.append(copy.deepcopy(doc))

        class _Res:
            inserted_id = doc.get('_id')

        return _Res()

    def _filtered(self, query: dict) -> list[dict]:
        return [d for d in self._docs if _match(d, query or {})]

    async def find_one(self, query: dict, *args, **kwargs):
        for d in self._docs:
            if _match(d, query or {}):
                return copy.deepcopy(d)
        return None

    def find(self, query: dict | None = None, *args, **kwargs):
        matched = [copy.deepcopy(d) for d in self._filtered(query or {})]
        return AsyncCursor(matched)

    async def replace_one(self, query: dict, doc: dict):
        for i, d in enumerate(self._docs):
            if _match(d, query):
                self._docs[i] = copy.deepcopy(doc)
                return _Result(matched=1, modified=1)
        return _Result(matched=0, modified=0)

    async def update_one(self, query: dict, updates: dict):
        for d in self._docs:
            if _match(d, query):
                _apply_set(d, updates)
                return _Result(matched=1, modified=1)
        return _Result(matched=0, modified=0)

    async def update_many(self, query: dict, updates: dict):
        count = 0
        for d in self._docs:
            if _match(d, query):
                _apply_set(d, updates)
                count += 1
        return _Result(matched=count, modified=count)

    async def delete_one(self, query: dict):
        for i, d in enumerate(self._docs):
            if _match(d, query):
                self._docs.pop(i)
                return _Result(deleted=1)
        return _Result(deleted=0)

    async def delete_many(self, query: dict):
        keep = [d for d in self._docs if not _match(d, query)]
        deleted = len(self._docs) - len(keep)
        self._docs = keep
        return _Result(deleted=deleted)

    async def find_one_and_update(self, query: dict, updates: dict, return_document=True):
        for d in self._docs:
            if _match(d, query):
                _apply_set(d, updates)
                return copy.deepcopy(d)
        return None

    async def create_index(self, *args, **kwargs):
        return 'idx'

    async def aggregate(self, pipeline: list[dict]):
        # поддерживаем только $group с $sum:1 по _id='$field'
        if not pipeline or '$group' not in pipeline[0]:
            return AsyncCursor([])
        group = pipeline[0]['$group']
        id_field = group['_id'].lstrip('$')
        counter: dict = {}
        for d in self._docs:
            key = d.get(id_field)
            counter[key] = counter.get(key, 0) + 1
        result = [{'_id': k, 'count': v} for k, v in counter.items()]
        return AsyncCursor(result)

    async def distinct(self, field: str):
        out = set()
        for d in self._docs:
            v = d.get(field)
            if isinstance(v, list):
                out.update(v)
            else:
                out.add(v)
        return list(out)

    # удобно для тестов
    def all_docs(self):
        return [copy.deepcopy(d) for d in self._docs]


class _Result:
    def __init__(self, matched=0, modified=0, deleted=0):
        self.matched_count = matched
        self.modified_count = modified
        self.deleted_count = deleted


class FakeDatabase:
    def __init__(self):
        self._collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        if name not in self._collections:
            self._collections[name] = FakeCollection()
        return self._collections[name]

    def __getattr__(self, name: str) -> FakeCollection:
        if name.startswith('_'):
            raise AttributeError(name)
        return self[name]

    async def command(self, *a, **k):
        return {'ok': 1}

    def reset(self):
        self._collections.clear()
