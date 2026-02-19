from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from models import Expense, session
from dotenv import load_dotenv
from sqlalchemy import func
from datetime import datetime

import os

load_dotenv()
TOKEN = os.getenv("TOKEN")

MENU, ADD, REMOVE = range(3)



async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("Add expense", callback_data="add")],
        [InlineKeyboardButton("Remove expense", callback_data="remove")],
        [InlineKeyboardButton("List expenses", callback_data="list")],
        [InlineKeyboardButton("Sum month", callback_data="sum_month")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.reply_text(
            "Please choose an option:", reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "Please choose an option:", reply_markup=reply_markup
        )
    return MENU

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await show_menu(update, context)


async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = update.message.text
        amount = float(text)
        user_id = update.effective_user.id

        new_expense = Expense(
            user_id=user_id,
            amount=amount,
        )
        session.add(new_expense)
        session.commit()

        await update.message.reply_text(
            f"✅ Added expense:\n€{amount}"
        )
        return await show_menu(update, context)

    except ValueError:
        await update.message.reply_text(
            "❌ Format error.\nUse: 50"
        )
        return await show_menu(update, context)
    
async def remove_expense(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = update.message.text
        expense_id = int(text)
        user_id = update.effective_user.id

        expense = session.query(Expense).filter_by(id=expense_id, user_id=user_id).first()

        
        if not expense:
            await update.message.reply_text("❌ Expense not found. Make sure the ID is correct.")
            return REMOVE

        session.delete(expense)
        session.commit()
        await update.message.reply_text(f"✅ Deleted expense ID {expense_id} (€{expense.amount})")
        return await show_menu(update, context)

    except ValueError:
        await update.message.reply_text("❌ Enter a valid number (the ID of the expense).")
        return REMOVE
    

async def list_expenses_generator(update, context) -> None:
    user_id = update.effective_user.id
    expenses = session.query(Expense).filter_by(user_id=user_id).all()

    # Determine chat/message to reply to
    if update.callback_query:
        # Inline button press
        message = update.callback_query.message
    else:
        # Normal command or message
        message = update.message

    if not expenses:
        await message.reply_text("No expenses yet.")
        return await show_menu(update, context)

    text = "\n".join([f"{e.id} - €{e.amount} ({e.date})" for e in expenses])
    await message.reply_text(f"📝 Your expenses:\n{text}")

async def list_expenses(update, context) -> int:
    await list_expenses_generator(update, context)
    return await show_menu(update, context)

async def sum_month(update, context) -> None:
    user_id = update.effective_user.id

    now = datetime.now()
    start_month = datetime(now.year, now.month, 1)

    if now.month == 12:
        end_month = datetime(now.year + 1, 1, 1)
    else:
        end_month = datetime(now.year, now.month + 1, 1)


    total = (
        session.query(func.sum(Expense.amount))
        .filter(
            Expense.user_id == user_id,
            Expense.date >= start_month,
            Expense.date < end_month
        )
        .scalar()
    )

    total = total or 0

    await update.callback_query.message.reply_text(f"💰 This month total: €{total}")

    return await show_menu(update, context)



async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "add":
        await query.edit_message_text(
            "✏️ Enter expense as a number like:\t50"
        )
        return ADD
    elif query.data == "remove":
        await list_expenses_generator(update, context)
        await update.callback_query.message.reply_text(
            "✏️ Enter the ID of the expense you want to remove:"
        )
        return REMOVE
    elif query.data == "list":
        await query.edit_message_text("📝 Listing your expenses...")
        await list_expenses(update, context)
        return MENU
    elif query.data == "sum_month":
        await query.edit_message_text("🧮 Calculating your month expenses...")
        await sum_month(update, context)
        return MENU
    else:
        await query.edit_message_text("Unknown option selected.")
        return await show_menu(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


def main():
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .read_timeout(10)
        .write_timeout(10)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [CallbackQueryHandler(button)],
            ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense)],
            REMOVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_expense)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == "__main__":
    main()