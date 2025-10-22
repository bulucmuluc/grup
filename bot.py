import os
import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError 

load_dotenv()

try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")  # Bot Token Okunuyor
    TARGET_GROUP_ID = int(os.getenv("TARGET_GROUP_ID"))
    SOURCE_CHANNEL_ID = os.getenv("SOURCE_CHANNEL_ID")
except (TypeError, ValueError) as e:
    print("HATA: .env dosyasındaki değişkenler eksik veya hatalı biçimde. Lütfen kontrol edin.")
    raise SystemExit(e)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- KARMA OTURUM BAŞLATILIYOR (Kullanıcı Hesabı + Bot Token) ---
app = Client(
    "user_session",  # Oturum dosya adı
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN  # Bot Token Eklendi
)

# --- Mesaj Silme Görevi ---
async def scheduled_deletion(client: Client, chat_id: int, message_ids: list):
    DELAY = 10 * 60 
    logging.info(f"Silme işlemi {chat_id} sohbetindeki {message_ids} mesajları için {DELAY} saniye sonraya planlandı.")
    
    await asyncio.sleep(DELAY)
    
    try:
        await client.delete_messages(
            chat_id=chat_id,
            message_ids=message_ids
        )
        logging.info(f"Mesajlar {message_ids} başarıyla silindi.")
    except Exception as e:
        logging.error(f"Mesajlar {message_ids} silinirken hata oluştu: {e}")

# --- Ana Mesaj İşleyici ---
@app.on_message(
    filters.chat(TARGET_GROUP_ID) & 
    filters.text &                 
    ~filters.via_bot               
)
async def all_message_handler(client: Client, message: Message):
    if not message.text or len(message.text) < 3:
        logging.debug("Kısa veya boş mesaj, işlenmiyor.")
        return 
        
    search_query = message.text
    logging.info(f"Gruptan gelen mesaj: '{search_query}'. Kaynak kanalda arama yapılıyor...")
    
    kaynak_mesaj = None
    
    try:
        # search_messages (Kullanıcı hesabı yetkisiyle çalışır)
        async for msg in client.search_messages(
            chat_id=SOURCE_CHANNEL_ID,
            query=search_query,
            limit=1
        ):
            kaynak_mesaj = msg
            break
        
        if kaynak_mesaj:
            
            # copy (Bot yetkisiyle gönderilir)
            copied_message = await kaynak_mesaj.copy(
                chat_id=message.chat.id
            )
            
            logging.info(f"Kaynak kanaldan mesaj ID: {kaynak_mesaj.id} başarıyla kopyalandı.")

            messages_to_delete_ids = [message.id, copied_message.id]

            asyncio.create_task(
                scheduled_deletion(
                    client, 
                    message.chat.id, 
                    messages_to_delete_ids
                )
            )
            
        else:
            logging.warning(f"Kaynak kanalda '{search_query}' kelimesiyle eşleşen mesaj bulunamadı. Sessiz kalınıyor.")
        
    except RPCError as e:
        logging.error(f"Telegram API Hatası ({e.CODE}): {e.MESSAGE}. Mesaj işlenemedi.")
    except Exception as e:
        logging.error(f"Beklenmedik bir hata oluştu: {e}")

if __name__ == "__main__":
    logging.info("Bot Oturumu başlatılıyor. İlk çalıştırmada kullanıcı girişi gerekebilir...")
    app.run()
