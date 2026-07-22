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
model = genai.GenerativeModel(model_name="gemini-3.5-flash", generation_config=generation_config)

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
        # Read file as raw bytes for inline data (bypasses upload_file discovery bug)
        with open(temp_file_path, "rb") as f:
            file_data = f.read()
        
        mime_type = "application/pdf" if temp_file_path.endswith(".pdf") else "image/jpeg"
        if suffix in [".png"]:
            mime_type = "image/png"
            
        prompt = """
        Extract the following information from this Fixed Deposit document.
        Return ONLY a valid JSON object matching the keys below. Do NOT include any comments (//), trailing commas, or markdown formatting.
        {
          "bank_code": "MBB",
          "account_full": "1234567890",
          "principal": 50000.00,
          "interest_rate": 3.85,
          "maturity_date": "2024-12-31"
        }
        (Note: bank_code should be a 3-4 letter shortcode for the bank. principal and interest_rate should be numbers, not strings).
        """
        
        # Send inline data directly to the model
        response = model.generate_content([
            {"mime_type": mime_type, "data": file_data},
            prompt
        ])
        
        os.remove(temp_file_path)
        
        import re
        
        raw_text = response.text.strip()
        
        # Clean markdown code blocks
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].strip()
            
        # Robustly extract JSON object using regex if there's still surrounding text
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = raw_text[start_idx:end_idx+1]
        else:
            json_str = raw_text
            
        # Clean up any trailing commas that might break json.loads
        json_str = re.sub(r',\s*\}', '}', json_str)
            
        result = json.loads(json_str)
        
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
