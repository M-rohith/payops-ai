# PayOps AI Agent Guide

PayOps AI is a payment-operations copilot project. The agreed stack is Next.js, TypeScript, and Tailwind CSS for the frontend; FastAPI and Python for the backend; and PostgreSQL for persistence.

## Working rules

- Prefer clear, modular code and small, focused modules.
- Never commit secrets. Use environment variables and keep local `.env` files ignored.
- Keep business calculations and data shaping in the backend, not the frontend.
- The frontend should primarily display data returned by backend APIs.
- A future PayOps AI LLM must use controlled backend tools, never unrestricted direct database access.
- Do not introduce major frameworks or replace the agreed stack without explicit instruction.
- Run relevant tests, linting, and type checks before declaring a task complete.
- Avoid implementing future phases unless explicitly requested.

