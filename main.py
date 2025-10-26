<<<<<<< HEAD
import os
import tkinter as tk
from tkinter import scrolledtext, simpledialog
import google.generativeai as genai
from dotenv import load_dotenv

# .env dosyasını yükle ve ortam değişkenlerini ayarla
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# --- Gemini Kurulumu ve İstemci Oluşturma ---
if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        
        # GenerativeModel oluştur
        # gemini-1.5-flash hem hızlı hem de chat için uygun bir modeldir.
        chat_model = genai.GenerativeModel('gemini-1.5-flash')
        
    except Exception as e:
        # Anahtar geçersizse veya bağlantı hatası varsa
        print(f"Gemini istemcisi başlatılamadı: {e}")
        chat_model = None # Modeli None olarak ayarla
else:
    chat_model = None
    print("Hata: GEMINI_API_KEY bulunamadı. Lütfen .env dosyanızı kontrol edin.")
    
# --- Tkinter Uygulama Sınıfı ---
class ChatApp:
    def __init__(self, master, chat_model):
        self.master = master
        master.title("Gemini Sohbet Uygulaması")
        self.chat_model = chat_model
        
        # Kullanıcı arayüzü elemanlarını oluştur
        self.chat_history = scrolledtext.ScrolledText(master, wrap=tk.WORD, state='disabled', width=80, height=20)
        self.chat_history.pack(padx=10, pady=10)
        
        self.user_input = tk.Entry(master, width=80)
        self.user_input.pack(padx=10, pady=5)
        self.user_input.bind("<Return>", self.send_message_event) # Enter tuşuna basınca mesaj gönder
        
        self.send_button = tk.Button(master, text="Gönder", command=self.send_message)
        self.send_button.pack(padx=10, pady=5)
        
        # İlk mesaj
        self.append_message("Gemini", "Merhaba! Ben Gemini. Nasılsın? Sohbet etmeye başlayabiliriz.")

        if not self.chat_model:
             self.append_message("Sistem", "HATA: API Anahtarı eksik veya geçersiz. Uygulama çalışmayacak.", color='red')
             self.send_button.config(state=tk.DISABLED)


    def append_message(self, sender, message, color='black'):
        """Sohbet geçmişine mesaj ekler."""
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, f"{sender}: ", (sender,))
        self.chat_history.tag_config(sender, foreground=color, font=('Arial', 10, 'bold'))
        self.chat_history.insert(tk.END, f"{message}\n\n")
        self.chat_history.config(state='disabled')
        self.chat_history.yview(tk.END) # En alta kaydır
        
    def send_message_event(self, event):
        """Enter tuşu için tetikleyici."""
        self.send_message()

    def send_message(self):
        """Kullanıcının mesajını gönderir ve Gemini'dan yanıt alır."""
        if not self.chat_model:
            return

        user_text = self.user_input.get()
        if not user_text.strip():
            return # Boş mesaj gönderme

        self.append_message("Sen", user_text, color='blue')
        self.user_input.delete(0, tk.END) # Giriş alanını temizle
        
        # Yükleme mesajı göster
        self.append_message("Gemini", "Yazıyor...", color='gray')
        
        try:
            # Gemini'a mesajı gönder
            response = self.chat_model.generate_content(user_text)
            
            # "Yazıyor..." mesajını sil
            self.chat_history.config(state='normal')
            end_index = self.chat_history.index(tk.END)
            # En son eklenen "Yazıyor..." mesajını silmek için biraz karmaşık bir indexleme
            # Basitçe son satırı silmek yeterli olacaktır:
            last_line = float(self.chat_history.index(tk.END)) - 2
            self.chat_history.delete(f"{last_line}", f"{last_line + 1}")
            self.chat_history.config(state='disabled')
            
            # Gerçek yanıtı göster
            self.append_message("Gemini", response.text, color='green')
            
        except Exception as e:
            # Hata durumunda yükleme mesajını silip hata mesajını göster
            self.chat_history.config(state='normal')
            self.chat_history.delete(f"{last_line}", f"{last_line + 1}")
            self.chat_history.config(state='disabled')
            self.append_message("HATA", f"API Hatası: {e}", color='red')
            
# --- Uygulamayı Başlatma ---
if __name__ == "__main__":
    if chat_model:
        root = tk.Tk()
        app = ChatApp(root, chat_model)
        root.mainloop()
    else:
        print("Gemini model başlatılamadı. Lütfen API anahtarınızı kontrol edin.")

        
=======
import streamlit as st

st.write("Hello")
>>>>>>> 92cdd3cccb8bf69ffd08e8f25001ff122ce30638
