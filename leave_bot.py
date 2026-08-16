import os
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, 
    CallbackQueryHandler, ConversationHandler, MessageHandler, filters
)

# --- CONFIGURATION ---
BOT_TOKEN = "8726077460:AAGOM1P46JDKs9K4NByHHVI45n5inVnkwM4"
OFFICE_CHAT_ID = "5745313495"

# PDF Templates
SICK_LEAVE_TEMPLATE = "sick_leave_form.pdf"
ANNUAL_LEAVE_TEMPLATE = "annual_leave_form.pdf"

TYPE, DATES, REASON = range(3)
leave_requests = {}

# --- DUAL PDF FORM FILLER FUNCTION ---
def fill_official_pdf(output_filename, req_data, supervisor_name, manager_name):
    leave_type = req_data.get('type', '')
    
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 10)

    # 1. ސަލާމް ފޯމު ނަމަ ފިލްކުރާނެ ފީލްޑްތައް (Coordinates)
    if leave_type == "Sick Leave":
        template_file = SICK_LEAVE_TEMPLATE
        
        # ސަލާމް ފޯމުގެ X, Y Coordinate ތައް:
        can.drawString(150, 680, str(req_data.get('user_name', ''))) # މުވައްޒަފުގެ ނަން
        can.drawString(150, 650, str(req_data.get('dates', '')))     # ސަލާމް ބުނި ތާރީޚު
        can.drawString(150, 620, str(req_data.get('reason', '')))    # ސަބަބު / ބަލީގެ ތަފްސީލު
        
        # ސޮއި/އެޕްރޫވަލް
        can.drawString(120, 480, f"{supervisor_name} (Digitally Approved)") 
        can.drawString(370, 480, f"{manager_name} (Digitally Approved)")   

    # 2. ޗުއްޓީ ފޯމު ނަމަ ފިލްކުރާނެ ފީލްޑްތައް (Coordinates)
    else:
        template_file = ANNUAL_LEAVE_TEMPLATE
        
        # ޗުއްޓީ ފޯމުގެ X, Y Coordinate ތައް:
        can.drawString(150, 690, str(req_data.get('user_name', ''))) # މުވައްޒަފުގެ ނަން
        can.drawString(150, 665, str(req_data.get('type', '')))      # ޗުއްޓީގެ ބާވަތް
        can.drawString(150, 640, str(req_data.get('dates', '')))     # ފަށާ / ނިމޭ ތާރީޚު
        can.drawString(150, 615, str(req_data.get('reason', '')))    # ސަބަބު
        
        # ސޮއި/އެޕްރޫވަލް
        can.drawString(120, 450, f"{supervisor_name} (Digitally Approved)") 
        can.drawString(370, 450, f"{manager_name} (Digitally Approved)")   

    can.save()
    packet.seek(0)

    # 3. Overlay އާއި އަސްލު PDF Template އެއްކޮށްލުން (Merge)
    new_pdf = PdfReader(packet)
    
    if os.path.exists(template_file):
        existing_pdf = PdfReader(template_file)
        output = PdfWriter()
        
        page = existing_pdf.pages[0]
        page.merge_page(new_pdf.pages[0])
        output.add_page(page)

        with open(output_filename, "wb") as output_stream:
            output.write(output_stream)
    else:
        # Template ނެތްނަމަ ވަގުތީ PDF އެއް ހެދުން
        with open(output_filename, "wb") as f:
            f.write(packet.getvalue())

# --- BOT CONVERSATION FLOW ---
async def start_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    context.user_data['user_name'] = user.full_name
    
    keyboard = [
        [InlineKeyboardButton("🤒 ސަލާމް (Sick Leave)", callback_data="Sick Leave")],
        [InlineKeyboardButton("🏖️ އަހަރީ ޗުއްޓީ (Annual Leave)", callback_data="Annual Leave")],
        [InlineKeyboardButton("👶 ޢާއިލީ ޗުއްޓީ (Family Leave)", callback_data="Family Leave")],
        [InlineKeyboardButton("🚨 ކުއްލި ޗުއްޓީ (Emergency Leave)", callback_data="Emergency Leave")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("މަރުޙަބާ! އެދެން ބޭނުންވާ ބާވަތެއް ތިރީގައިވާ ބަޓަންތަކުން ޚިޔާރުކުރައްވާ:", reply_markup=reply_markup)
    return TYPE

async def type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['type'] = query.data
    
    # ސަލާމާއި ޗުއްޓީއަށް ވަކިން ސުވާލުކުރުން
    if query.data == "Sick Leave":
        prompt_text = "ސަލާމް ބުނި ތާރީޚު (ނުވަތަ މުއްދަތު) ލިޔުއްވާ:\n*(މިސާލަކަށް: 17 Aug 2026)*"
    else:
        prompt_text = "ޗުއްޓީ ފަށާ ތާރީޚާއި ނިމޭ ތާރީޚު ލިޔުއްވާ:\n*(މިސާލަކަށް: 17 Aug 2026 - 25 Aug 2026)*"

    await query.edit_message_text(
        f"ޚިޔާރުކުރެއްވީ: **{query.data}**\n\n{prompt_text}",
        parse_mode="Markdown"
    )
    return DATES

async def dates_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dates'] = update.message.text
    await update.message.reply_text("ސަލާމް/ޗުއްޓީ ނަގާ ސަބަބު ތަފްސީލުކޮށް ލިޔުއްވާ:")
    return REASON

async def reason_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['reason'] = update.message.text
    user_id = update.message.from_user.id
    
    leave_requests[user_id] = context.user_data.copy()
    
    await update.message.reply_text("✅ ޝުކުރިއްޔާ! ތިޔަ އެދިވަޑައިގެންނެވި ފޯމު އެޕްރޫވަލްއަށް ފޮނުވިއްޖެ.")
    
    keyboard = [
        [
            InlineKeyboardButton("Approve (Supervisor)", callback_data=f"sup_app_{user_id}"),
            InlineKeyboardButton("Reject", callback_data=f"reject_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (f"🚨 **NEW REQUEST** 🚨\n\n"
           f"👤 **Employee:** {context.user_data['user_name']}\n"
           f"📋 **Type:** {context.user_data['type']}\n"
           f"📅 **Dates:** {context.user_data['dates']}\n"
           f"📝 **Reason:** {context.user_data['reason']}\n\n"
           f"--- Supervisor Approval Needed ---")
    
    await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=reply_markup, parse_mode="Markdown")
    return ConversationHandler.END

# --- APPROVAL HANDLERS ---
async def handle_approvals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    approver_name = query.from_user.full_name
    
    if data.startswith("sup_app_"):
        emp_id = int(data.split("_")[2])
        if emp_id not in leave_requests:
            await query.edit_message_text("❌ Request expired or not found.")
            return

        leave_requests[emp_id]['supervisor'] = approver_name
        
        keyboard = [
            [
                InlineKeyboardButton("Approve (Manager)", callback_data=f"man_app_{emp_id}"),
                InlineKeyboardButton("Reject", callback_data=f"reject_{emp_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{query.message.text}\n\n✅ **Approved by Supervisor:** {approver_name}\n\n--- Manager Approval Needed ---",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    elif data.startswith("man_app_"):
        emp_id = int(data.split("_")[2])
        if emp_id not in leave_requests:
            await query.edit_message_text("❌ Request expired or not found.")
            return

        req = leave_requests[emp_id]
        req['manager'] = approver_name
        
        await query.edit_message_text(
            f"{query.message.text}\n\n✅ **Approved by Manager:** {approver_name}\n\n🎉 **FULLY APPROVED! Generating Form...**",
            parse_mode="Markdown"
        )
        
        # Generate filled PDF based on request type
        pdf_filename = f"Filled_Form_{emp_id}.pdf"
        fill_official_pdf(pdf_filename, req, req['supervisor'], req['manager'])
        
        # Send to HR
        with open(pdf_filename, 'rb') as pdf_file:
            await context.bot.send_document(
                chat_id=OFFICE_CHAT_ID,
                document=pdf_file,
                caption=f"📄 Signed Form ({req['type']})\nEmployee: {req['user_name']}"
            )
            
        if os.path.exists(pdf_filename):
            os.remove(pdf_filename)

    elif data.startswith("reject_"):
        await query.edit_message_text(f"❌ **Request Rejected by {approver_name}**", parse_mode="Markdown")

# --- MAIN FUNCTION ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_leave), CommandHandler('leave', start_leave), CommandHandler('salam', start_leave)],
        states={
            TYPE: [CallbackQueryHandler(type_chosen)],
            DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, dates_received)],
            REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, reason_received)],
        },
        fallbacks=[],
        per_message=False
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_approvals))

    print("Bot is running with Dual Form logic...")
    app.run_polling()

if __name__ == '__main__':
    main()