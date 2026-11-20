from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app) # Чтобы браузер не блокировал запросы

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Настройки бота (база знаний для Бухты Знаний)
SYSTEM_PROMPT = """
Ты — вежливый и заботливый администратор детского центра «Бухта Знаний».
Твоя задача — отвечать на вопросы родителей, рассказывать о занятиях и записывать на пробные занятия.

ИНФОРМАЦИЯ О ЦЕНТРЕ:
- Адрес: г. Москва, ул. Новочерёмушкинская, д. 71/32. Внутри закрытой территории ЖК.
- Телефон: +79164464888
- Почта: buhta_znaniy@mail.ru

ЗАНЯТИЯ И ЦЕНЫ:
1. Клуб друзей для школьников (по субботам, 2-3 раза в месяц). 2500₽ за 3 часа.
2. Полезная продлёнка (без гаджетов, забирают из школы 1948). До 12 детей, 1-3 класс. Пн-Пт 11:00-19:00. От 1610₽ в день при покупке месячного абонемента.
3. Спектакли и праздники (7-11 лет, выходные). Стоимость: 3000₽.
4. Мышематика (4-7 лет). Чт и Сб. 4 занятия — 6600₽, пробное — 1700₽ (в сентябре 1500₽), разовое — 2200₽.
5. Шахматы (с 5 лет, Вт 18:00-19:00). Разово — 2000₽, 4 занятия — 6000₽.
6. Игротека «Мафия против ютуба» (Сб 15:00-16:00). Для детей и подростков.
7. Школа общения (Дошкольники 5-7 лет Пт 18:30; Школьники 7-11 лет). Пробное — 500₽, разовое — 2000-2500₽, абонемент 4 занятия — 7500₽.

ПРАВИЛА ОБЩЕНИЯ:
1. Отвечай дружелюбно, кратко и по делу.
2. Если родитель хочет записаться, предложи оставить имя и номер телефона.
3. ОБЯЗАТЕЛЬНО: как только родитель отправляет номер телефона, ты должен написать: "Спасибо! Я передал ваш номер. С вами свяжется администратор. Отправляя номер, вы даете согласие на обработку персональных данных в соответствии с политикой конфиденциальности."
4. Если не знаешь точного ответа (например, есть ли места в конкретной группе), скажи: "Уточню у администратора и вернусь к вам" или предложи позвонить по номеру +79164464888.
"""

# HTML-страница с чатом (встроена прямо в код для простоты)
HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Чат с Бухтой Знаний</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .chat-container { width: 400px; height: 600px; background: white; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); display: flex; flex-direction: column; overflow: hidden; }
        .chat-header { background: #4a90e2; color: white; padding: 15px; text-align: center; font-weight: bold; }
        .chat-messages { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .message { max-width: 80%; padding: 10px 15px; border-radius: 15px; font-size: 14px; }
        .message.user { background: #e3f2fd; align-self: flex-end; border-bottom-right-radius: 2px; }
        .message.bot { background: #f1f1f1; align-self: flex-start; border-bottom-left-radius: 2px; }
        .chat-input { display: flex; padding: 10px; border-top: 1px solid #ddd; }
        .chat-input input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 20px; outline: none; }
        .chat-input button { margin-left: 10px; padding: 10px 20px; background: #4a90e2; color: white; border: none; border-radius: 20px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">Бухта Знаний</div>
        <div class="chat-messages" id="messages">
            <div class="message bot">Здравствуйте! Чем могу помочь?</div>
        </div>
        <div class="chat-input">
            <input type="text" id="user-input" placeholder="Напишите сообщение..." onkeypress="if(event.key === 'Enter') sendMessage()">
            <button onclick="sendMessage()">Отправить</button>
        </div>
    </div>

    <script>
        async function sendMessage() {
            const input = document.getElementById('user-input');
            const text = input.value.trim();
            if (!text) return;

            // Показываем сообщение пользователя
            addMessage(text, 'user');
            input.value = '';

            try {
                // Отправляем на сервер
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                const data = await response.json();
                addMessage(data.reply, 'bot');
            } catch (error) {
                addMessage('Ошибка соединения с сервером.', 'bot');
            }
        }

        function addMessage(text, sender) {
            const messagesDiv = document.getElementById('messages');
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${sender}`;
            msgDiv.innerText = text;
            messagesDiv.appendChild(msgDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    try:
        response = client.chat.completions.create(
            model="gpt-6-luna",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            max_completion_tokens=500,
            reasoning_effort="none"
        )
        reply = response.choices[0].message.content
    except Exception as e:
        print(f"Ошибка OpenAI: {e}")
        reply = "Извините, произошла ошибка. Попробуйте позже."
        
    return jsonify({"reply": reply})

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    print(f"Веб-бот запущен на порту {port}")
    app.run(host="0.0.0.0", port=port)