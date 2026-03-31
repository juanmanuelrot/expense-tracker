"""AI service for parsing expenses from text, receipts, and audio using Claude API."""

import base64
import json
from datetime import date
from decimal import Decimal
from typing import Any

import anthropic

from app.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

EXPENSE_TOOL = {
    "name": "record_expense",
    "description": "Record a parsed expense from user input. Extract all available information.",
    "input_schema": {
        "type": "object",
        "properties": {
            "amount": {
                "type": "number",
                "description": "The total amount spent",
            },
            "currency": {
                "type": "string",
                "enum": ["UYU", "USD"],
                "description": "Currency. 'pesos' = UYU, 'dólares'/'dollars' = USD. Bare '$' defaults to UYU unless context suggests USD.",
            },
            "description": {
                "type": "string",
                "description": "Short description of the expense",
            },
            "merchant": {
                "type": "string",
                "description": "Store, restaurant, or business name if mentioned",
            },
            "category": {
                "type": "string",
                "enum": [
                    "Food & Dining",
                    "Groceries",
                    "Transport",
                    "Entertainment",
                    "Shopping",
                    "Bills & Utilities",
                    "Health",
                    "Travel",
                    "Education",
                    "Home",
                    "Personal Care",
                    "Subscriptions",
                    "Income",
                    "Other",
                ],
                "description": "Best matching expense category",
            },
            "expense_date": {
                "type": "string",
                "description": "Date of expense in YYYY-MM-DD format. Use today if not specified.",
            },
            "account_hint": {
                "type": "string",
                "description": "Any hint about which bank account or card was used (e.g. 'BROU débito', 'Itaú crédito', 'efectivo')",
            },
            "split_with": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "person_name": {"type": "string"},
                        "amount": {
                            "type": "number",
                            "description": "Amount this person owes. If split equally, divide total by number of people.",
                        },
                    },
                    "required": ["person_name", "amount"],
                },
                "description": "If the expense was shared/split with others, list who owes what",
            },
            "is_income": {
                "type": "boolean",
                "description": "True if this is income/reimbursement rather than an expense",
            },
            "confidence": {
                "type": "number",
                "description": "Your confidence in the parsing from 0.0 to 1.0",
            },
        },
        "required": ["amount", "currency", "description", "category", "expense_date", "confidence"],
    },
}

RECEIPT_TOOL = {
    "name": "record_receipt",
    "description": "Extract structured data from a receipt image.",
    "input_schema": {
        "type": "object",
        "properties": {
            "merchant": {
                "type": "string",
                "description": "Store/business name from receipt header",
            },
            "merchant_address": {
                "type": "string",
                "description": "Store address if visible",
            },
            "expense_date": {
                "type": "string",
                "description": "Date on receipt in YYYY-MM-DD format",
            },
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_price": {"type": "number"},
                        "amount": {"type": "number"},
                    },
                    "required": ["description", "amount"],
                },
            },
            "subtotal": {"type": "number"},
            "tax": {"type": "number"},
            "tip": {"type": "number"},
            "total": {
                "type": "number",
                "description": "Final total amount on receipt",
            },
            "currency": {
                "type": "string",
                "enum": ["UYU", "USD"],
                "description": "Currency. Default UYU for Uruguayan receipts.",
            },
            "payment_method": {
                "type": "string",
                "description": "Payment method shown on receipt (e.g. 'Visa', 'efectivo', 'débito')",
            },
            "category": {
                "type": "string",
                "enum": [
                    "Food & Dining",
                    "Groceries",
                    "Transport",
                    "Entertainment",
                    "Shopping",
                    "Bills & Utilities",
                    "Health",
                    "Travel",
                    "Education",
                    "Home",
                    "Personal Care",
                    "Subscriptions",
                    "Income",
                    "Other",
                ],
            },
            "confidence": {"type": "number"},
        },
        "required": ["merchant", "total", "currency", "category", "expense_date", "confidence"],
    },
}


def _build_system_prompt(user_accounts: list[dict] | None = None, user_categories: list[str] | None = None) -> str:
    today = date.today().isoformat()
    prompt = f"""You are an expense tracking assistant for a user in Uruguay. Today's date is {today}.

Key rules:
- Default currency is UYU (Peso Uruguayo). "pesos" = UYU. "dólares"/"dollars" = USD.
- Bare "$" sign without context means UYU.
- "U$S" or "US$" or "USD" means US dollars.
- The user may write in Spanish or English.
- Extract as much information as possible from the input.
- If the user mentions paying for friends or splitting, extract split information.
- If someone paid the user back, mark it as income/reimbursement.
"""

    if user_accounts:
        prompt += "\nUser's accounts and cards:\n"
        for acc in user_accounts:
            prompt += f"- {acc['name']} ({acc['institution']}, {acc['type']})"
            if acc.get("last_four"):
                prompt += f" ending in {acc['last_four']}"
            prompt += "\n"

    return prompt


async def parse_expense_text(
    text: str,
    user_accounts: list[dict] | None = None,
) -> dict[str, Any]:
    """Parse a natural language expense description into structured data."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=_build_system_prompt(user_accounts),
        tools=[EXPENSE_TOOL],
        tool_choice={"type": "tool", "name": "record_expense"},
        messages=[{"role": "user", "content": text}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_expense":
            return block.input

    return {"error": "Could not parse expense from text", "raw": text}


async def parse_receipt_image(
    image_data: bytes,
    media_type: str = "image/jpeg",
    user_accounts: list[dict] | None = None,
) -> dict[str, Any]:
    """Parse a receipt image into structured expense data using Claude vision."""
    b64_image = base64.b64encode(image_data).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=_build_system_prompt(user_accounts),
        tools=[RECEIPT_TOOL],
        tool_choice={"type": "tool", "name": "record_receipt"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract all information from this receipt. Identify the store, items, totals, and payment method.",
                    },
                ],
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_receipt":
            return block.input

    return {"error": "Could not parse receipt image"}
