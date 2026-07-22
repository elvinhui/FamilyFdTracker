import os
import asyncio
import google.generativeai as genai
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from db import DynamoDBHandler
import tempfile
import mimetypes

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
generation_config = {
  "temperature": 0.1,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 1024,
  "response_mime_type": "application/json",
}
model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

db = DynamoDBHandler()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏦 Welcome to the Family FD Tracker Bot!\n"
        "Send me a photo of a Fixed Deposit receipt and I will automatically extract its details and save it."
    )

async def process_document_or_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, file_obj, file_name: str, suffix: str):
    if not os.getenv("GEMINI_API_KEY"):
        await update.message.reply_text("Error: GEMINI_API_KEY is not configured on the server.")
        return

    await update.message.reply_text("Processing your document... Please wait ⏳")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        await file_obj.download_to_drive(temp_file.name)
        temp_file_path = temp_file.name

    try:
        # Upload to Gemini API
        uploaded_file = genai.upload_file(path=temp_file_path, display_name=file_name)
        
        prompt = """
        Extract the following information from this Fixed Deposit document. Return a JSON object exactly matching this schema:
        {
          "bank_code": "String (e.g., MBB, PBB, CIMB, HLB. Try to deduce a 3-4 letter shortcode for the bank)",
          "account_full": "String (The full account number of the fixed deposit)",
          "principal": "Number (The initial deposit amount, e.g., 50000.00)",
          "interest_rate": "Number (The interest rate percentage, e.g., 3.85)",
          "maturity_date": "String (The maturity date in YYYY-MM-DD format)"
        }
        """
        
        response = model.generate_content([uploaded_file, prompt])
        
        # Clean up gemini file
        genai.delete_file(uploaded_file.name)
        os.remove(temp_file_path)
        
        # Parse result (handling potential markdown code blocks)
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        result = json.loads(raw_text.strip())
        
        # Add to database
        db.add_deposit(
            bank_code=result.get("bank_code", "UNK"),
            account_full=result.get("account_full", "0000"),
            principal=float(result.get("principal", 0.0)),
            interest_rate=float(result.get("interest_rate", 0.0)),
            maturity_date=result.get("maturity_date", "1970-01-01")
        )
        
        account_tail = db.mask_account(result.get("account_full", ""))
        msg = (
            f"✅ Successfully added Fixed Deposit!\n\n"
            f"🏦 Bank: {result.get('bank_code')}\n"
            f"🔢 Account: {account_tail}\n"
            f"💰 Principal: ${result.get('principal')}\n"
            f"📈 Rate: {result.get('interest_rate')}%\n"
            f"📅 Maturity: {result.get('maturity_date')}"
        )
        await update.message.reply_text(msg)

    except Exception as e:
        await update.message.reply_text(f"❌ Failed to process document. Error: {str(e)}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    await process_document_or_photo(update, context, photo_file, "FD_Receipt_Photo", ".jpg")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if document.mime_type not in ['application/pdf', 'image/jpeg', 'image/png']:
        await update.message.reply_text("❌ Please send a PDF or an image file.")
        return
    
    doc_file = await document.get_file()
    suffix = mimetypes.guess_extension(document.mime_type) or ".pdf"
    await process_document_or_photo(update, context, doc_file, document.file_name or "FD_Receipt_Doc", suffix)

def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("BOT_TOKEN is not set. Telegram bot will not start.")
        return

    application = ApplicationBuilder().token(bot_token).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("Telegram bot started polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
