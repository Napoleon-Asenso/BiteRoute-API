---
name: coding-standards
trigger: always_on
description: Always-active coding standards enforcing PEP 8, strict Python 3.14 type annotations, Pydantic schemas, and centralized exceptions.
---

# Coding Standards Rule

**Scope:** Python, FastAPI, and Pydantic implementations  
**Rule File:** `.agents/rules/coding-standards.md`  
**Trigger:** `always_on` (Global)  
**Enforcement:** MANDATORY  

---

## 1. Style & Formatting (PEP 8)
- **ALWAYS** adhere strictly to PEP 8 style guidelines.
- **ALWAYS** keep lines within 100 characters where practical.
- **ALWAYS** use snake_case for functions, methods, and variable names.
- **ALWAYS** use PascalCase for class names and Pydantic schemas.
- **ALWAYS** use UPPERCASE_SNAKE_CASE for constants.

---

## 2. Type Annotations
- **ALWAYS** write explicit type annotations on every function parameter and return type.
  ```python
  # CORRECT:
  async def get_restaurant(restaurant_id: UUID, db: AsyncSession) -> RestaurantResponse:
      ...

  # FORBIDDEN:
  async def get_restaurant(restaurant_id, db):
      ...
  ```
- **ALWAYS** utilize native Python 3.14 types:
  - Use `list[T]`, `dict[K, V]`, `set[T]`, `tuple[T, ...]` instead of legacy `typing.List`, `typing.Dict`.
  - Use `T | None` instead of `Optional[T]`.
- **NEVER** use `Any` as a lazy shortcut. If a type is genuinely dynamic, use an explicit `Union` or generic `TypeVar`.

---

## 3. Pydantic Schemas & DTOs
- **ALWAYS** use Pydantic V2 (`BaseModel`, `Field`, `ConfigDict`) for all request bodies, query parameter containers, and response DTOs.
- **ALWAYS** configure `model_config = ConfigDict(from_attributes=True)` on response schemas that read from SQLAlchemy ORM models.
- **NEVER** return raw SQLAlchemy ORM model instances from route handlers.
- **ALWAYS** define field validations using Pydantic's `Field` (e.g. `Field(gt=0)`, `Field(min_length=1, max_length=255)`).

---

## 4. Documentation & Docstrings
- **ALWAYS** provide descriptive docstrings for all modules, classes, and public API endpoint functions.
- **ALWAYS** document endpoint query parameters, potential error responses, and return structures.

---

## 5. Error Handling & Exceptions
- **ALWAYS** define and raise explicit custom exceptions inheriting from `AppException` in `app/core/exceptions.py`.
- **NEVER** write bare `except:` clauses. Always catch specific exception types (`except IntegrityError:`, `except ValueError:`).
- **NEVER** return dictionary representations of errors directly from route handlers (e.g. `return {"error": "not found"}`). Always raise custom exceptions that trigger the global exception handlers.

---

## 6. Dependency Injection
- **ALWAYS** inject database sessions via FastAPI's dependency system (`db: AsyncSession = Depends(get_db)`).
- **ALWAYS** use `async with` context managers for transactions that execute multi-table mutations.
- **NEVER** instantiate ad-hoc database sessions directly inside business logic or route functions.
