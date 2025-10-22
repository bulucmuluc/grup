import os
import asyncio  # Zamanlayıcı için gerekli
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatType

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_GROUP_ID = int(os.getenv("TARGET_GROUP_ID"))
SOURCE_CHANNEL_ID = os.getenv("SOURCE_CHANNEL_ID")

# Sadece INFO seviyesindeki loglar gösterilecek
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Client(
    "all_message_copy_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Mesaj Silme Görevi ---
async def scheduled_deletion(client: Client, chat_id: int, message_ids: list):
    # 10 dakika = 600 saniye
    DELAY = 10 * 60 
    logging.info(f"Silme işlemi {chat_id} sohbetindeki {message_ids} mesajları için {DELAY} saniye sonraya planlandı.")
    
    await asyncio.sleep(DELAY)
    
    try:
        # Belirtilen mesaj kimliklerini sil
        await client.delete_messages(
            chat_id=chat_id,
            message_ids=message_ids
        )
        logging.info(f"Mesajlar {message_ids} başarıyla silindi.")
    except Exception as e:
        # Botun silme yetkisi yoksa veya mesaj zaten silinmişse hata loglanır, gruba mesaj gitmez.
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
    
    try:
        arama_sonuclari = await client.search_messages(
            chat_id=SOURCE_CHANNEL_ID,
            query=search_query,
            limit=1
        )
        
        if arama_sonuclari:
            kaynak_mesaj = arama_sonuclari[0]
            
            # 1. Kaynak mesajı kopyala
            copied_message = await kaynak_mesaj.copy(
                chat_id=message.chat.id
            )
            
            logging.info(f"Kaynak kanaldan mesaj ID: {kaynak_mesaj.id} başarıyla kopyalandı.")

            # 2. Silinmek üzere her iki mesajın ID'sini topla
            messages_to_delete_ids = [message.id, copied_message.id]

            # 3. Silme görevini asenkron olarak başlat (ana döngüyü engellemeden)
            asyncio.create_task(
                scheduled_deletion(
                    client, 
                    message.chat.id, 
                    messages_to_delete_ids
                )
            )
            
        else:
            logging.warning(f"Kaynak kanalda '{search_query}' kelimesiyle eşleşen mesaj bulunamadı. Sessiz kalınıyor.")
        
    except Exception as e:
        logging.error(f"Mesaj arama/kopyalama sırasında bir hata oluştu: {e}")

if __name__ == "__main__":
    logging.info("Bot başlatılıyor...")
    app.run()
  
