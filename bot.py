import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request
import telebot
import telebot.apihelper
from mercadopago import SDK

# Configura timeouts para evitar travamentos de rede
telebot.apihelper.CONNECT_TIMEOUT = 10
telebot.apihelper.READ_TIMEOUT = 10

TOKEN_TELEGRAM = "8749029036:AAFIjhRMCmJgolG3hvTnKK4oRNkROh6kVus"
TOKEN_MERCADO_PAGO = "APP_USR-1206418499058235-101014-5b5e7a243d400d764e212c528dbb0c07-346927061"
GRUPO_VIP_ID = "-1005447535477"
LINK_CONVITE_VIP = "https://t.me/+r_aqMlHEUZE4NjRh"
CHAVE_SECRETA_CRON = "SegredoDoBot123"

ADMIN_IDS = [7993936618, 8748519754]

bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=True)
mp = SDK(TOKEN_MERCADO_PAGO)
app = Flask(__name__)

import time

def enviar_mensagem_com_retry(chat_id, texto, parse_mode="Markdown", reply_markup=None, reply_to_message_id=None, retries=3):
    for i in range(retries):
        try:
            return bot.send_message(
                chat_id,
                texto,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id
            )
        except Exception as e:
            if i == retries - 1:
                raise e
            time.sleep(1)

def init_db():
    conn = sqlite3.connect('subscriptions.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subs (
            user_id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            expiry TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            descricao TEXT,
            valor REAL,
            data TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

CONTEUDOS = {
    "pix_30": {
        "valor": 30.00,
        "descricao": "Grupo VIP (30 dias)",
        "tipo": "grupo_vip"
    },
}

@app.route('/', methods=['POST'])
def getMessage():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

@app.route("/")
def home():
    return "Bot online e seguro!", 200

def executar_limpeza_expirados():
    conn = sqlite3.connect('subscriptions.db', check_same_thread=False)
    cursor = conn.cursor()
    agora_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("SELECT user_id, chat_id FROM subs WHERE expiry < ?", (agora_str,))
    expirados = cursor.fetchall()

    removidos = 0
    for user_id, chat_id in expirados:
        try:
            bot.ban_chat_member(GRUPO_VIP_ID, user_id)
            bot.unban_chat_member(GRUPO_VIP_ID, user_id)

            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                telebot.types.InlineKeyboardButton("❤️ Renovar Grupo VIP (30 dias) - R$ 30,00", callback_data="pix_30")
            )
            
            destino = chat_id if chat_id else user_id

            texto_expiracao = (
                "⚠️ *A sua assinatura do Grupo VIP expirou!*\n\n"
                "Poxa, o seu tempinho por lá acabou... 🥺 Mas você pode voltar "
                "a ter acesso imediato a todo o conteúdo exclusivo agora mesmo!\n\n"
                "Deseja renovar a sua assinatura por mais 30 dias?"
            )
            enviar_mensagem_com_retry(destino, texto_expiracao, parse_mode="Markdown", reply_markup=markup)

            cursor.execute("DELETE FROM subs WHERE user_id = ?", (user_id,))
            conn.commit()
            removidos += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"Erro ao remover usuário {user_id}: {e}")

    conn.close()
    return removidos

@app.route("/check_expirations", methods=['GET'])
def check_expirations():
    user_key = request.args.get('key')
    if user_key != CHAVE_SECRETA_CRON:
        return "Acesso negado. Chave inválida.", 403

    try:
        removidos = executar_limpeza_expirados()
        return f"Verificação concluída. {removidos} usuários removidos por expiração.", 200
    except Exception as e:
        return f"Erro: {e}", 500

@bot.message_handler(commands=['forcar_limpeza'])
def comando_forcar_limpeza(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "Acesso negado. Este comando é exclusivo da administração.")
        return
    
    bot.reply_to(message, "🔄 Executando a verificação de assinaturas expiradas...")
    total = executar_limpeza_expirados()
    bot.reply_to(message, f"✅ Limpeza concluída! Total de usuários expirados removidos e avisados: `{total}`", parse_mode="Markdown")

@bot.message_handler(commands=['limpar_geral'])
def limpar_geral(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "Acesso negado.")
        return

    try:
        conn = sqlite3.connect('subscriptions.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subs")
        removidos_total = cursor.rowcount
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ *Limpeza geral executada!*\n\nForam limpos `{removidos_total}` registros antigos da base de dados.", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao limpar base de dados: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("❤️ R$ 30,00 - Grupo VIP (30 dias)", callback_data="pix_30"),
    )
    texto = "✨ *Olá! Seja bem-vindo(a)*\n\nEscolha uma das opções abaixo para continuar. Bjss ❤️"
    bot.send_message(message.chat.id, texto, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['relatorio', 'painel'])
def relatorio_admin(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "Acesso negado. Este comando é exclusivo da administração.")
        return

    conn = sqlite3.connect('subscriptions.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM subs")
    total_ativos = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*), SUM(valor) FROM vendas")
    res_vendas = cursor.fetchone()
    total_vendas = res_vendas[0] if res_vendas[0] else 0
    faturamento_total = res_vendas[1] if res_vendas[1] else 0.0

    cursor.execute("SELECT descricao, COUNT(*) FROM vendas GROUP BY descricao")
    vendas_por_tipo = cursor.fetchall()

    cursor.execute("SELECT user_id, expiry FROM subs ORDER BY expiry ASC LIMIT 5")
    proximos = cursor.fetchall()
    conn.close()

    texto_relatorio = (
        f"📊 *PAINEL DE RELATÓRIOS E ESTATÍSTICAS*\n\n"
        f"👥 *Membros VIP Ativos:* `{total_ativos}`\n"
        f"📦 *Total de Vendas Realizadas:* `{total_vendas}`\n"
        f"💰 *Faturamento Total:* `R$ {faturamento_total:.2f}`\n\n"
        f"📋 *Vendas por Pacote:*\n"
    )

    if vendas_por_tipo:
        for desc, qtd in vendas_por_tipo:
            texto_relatorio += f"• {desc}: `{qtd}x`\n"
    else:
        texto_relatorio += "Nenhuma venda registrada ainda.\n"

    texto_relatorio += f"\n⏳ *Próximas Expirações (Grupo VIP):* \n"
    if proximos:
        for uid, exp in proximos:
            texto_relatorio += f"• ID `{uid}` — Expira: `{exp}`\n"
    else:
        texto_relatorio += "Nenhuma assinatura registrada no momento.\n"

    bot.reply_to(message, texto_relatorio, parse_mode="Markdown")

@bot.message_handler(commands=['liberar'])
def liberar_manual(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "Acesso negado. Este comando é exclusivo da administração.")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Uso correto: `/liberar ID_DO_USUARIO`", parse_mode="Markdown")
        return

    try:
        target_user_id = int(args[1])
        expiry_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')

        conn = sqlite3.connect('subscriptions.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO subs (user_id, chat_id, expiry) VALUES (?, ?, ?)", (target_user_id, message.chat.id, expiry_date))
        conn.commit()
        conn.close()

        markup_link = telebot.types.InlineKeyboardMarkup()
        markup_link.add(telebot.types.InlineKeyboardButton("🔗 Entrar no Grupo VIP", url=LINK_CONVITE_VIP))
        bot.reply_to(message, f"✅ Usuário `{target_user_id}` liberado com sucesso por 30 dias!", parse_mode="Markdown", reply_markup=markup_link)
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao liberar: {e}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    data = call.data

    if data.startswith('check_'):
        try:
            payment_id, opcao_original = data.replace('check_', '').split('.', 1)

            payment_info = mp.payment().get(payment_id)
            status = payment_info.get("response", {}).get("status")

            if status == "approved":
                item = CONTEUDOS.get(opcao_original)
                if item:
                    chat_id = call.message.chat.id
                    user_id = call.from_user.id
                    tipo = item.get("tipo")
                    descricao_venda = item.get("descricao")
                    valor_venda = item.get("valor")

                    conn = sqlite3.connect('subscriptions.db', check_same_thread=False)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO vendas (user_id, descricao, valor, data) VALUES (?, ?, ?, ?)",
                                   (user_id, descricao_venda, valor_venda, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

                    if tipo == "grupo_vip":
                        expiry_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
                        cursor.execute("REPLACE INTO subs (user_id, chat_id, expiry) VALUES (?, ?, ?)", (user_id, chat_id, expiry_date))
                        conn.commit()
                        conn.close()

                        markup_link = telebot.types.InlineKeyboardMarkup()
                        markup_link.add(telebot.types.InlineKeyboardButton("🔗 Entrar no Grupo VIP", url=LINK_CONVITE_VIP))
                        bot.send_message(chat_id, f"🎉 *Pagamento confirmado com sucesso!*\n\nClique no botão abaixo para entrar no Grupo VIP (Válido por 30 dias):", parse_mode="Markdown", protect_content=True, reply_markup=markup_link)

                    bot.send_message(chat_id, "✅ Pagamento aprovado e conteúdo enviado com sucesso!")
            else:
                bot.send_message(call.message.chat.id, "⏳ Pagamento ainda não foi identificado ou está pendente. Efetue o pagamento via Pix e tente novamente em instantes.")
        except Exception as e:
            print(f"Erro detalhado ao verificar pagamento: {e}")
            bot.send_message(call.message.chat.id, "⚠️ A consulta demorou a responder ou o pagamento ainda está processando. Clique novamente em verificar em instantes.")
        return

    if data in CONTEUDOS:
        item = CONTEUDOS[data]
        valor = float(item["valor"])
        descricao = item["descricao"]

        payment_data = {
            "transaction_amount": valor,
            "description": descricao,
            "payment_method_id": "pix",
            "payer": {"email": f"cliente_{call.from_user.id}@email.com"}
        }

        try:
            payment_response = mp.payment().create(payment_data)

            if "response" in payment_response and "id" in payment_response["response"]:
                payment_id = str(payment_response["response"]["id"])
                pix_code = payment_response["response"]["point_of_interaction"]["transaction_data"]["qr_code"]

                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton("🔄 Já fiz o pagamento / Verificar", callback_data=f"check_{payment_id}.{data}"))

                msg_texto = (
                    f"✅ *Cobrança gerada para: {descricao}*\n"
                    f"💰 *Valor:* R$ {valor:.2f}\n\n"
                    f"Copie a chave PIX Copia e Cola abaixo:\n\n"
                    f"`{pix_code}`\n\n"
                    f"⚡ _Após pagar, clique no botão abaixo para liberar o acesso automático!_"
                )
                bot.send_message(call.message.chat.id, msg_texto, parse_mode="Markdown", reply_markup=markup)
            else:
                erro_detalhado = str(payment_response)
                print(f"Erro MP Detalhado: {erro_detalhado}")
                bot.send_message(call.message.chat.id, f"❌ Erro ao gerar PIX no Mercado Pago. Tente novamente.")
        except Exception as e:
            print(f"Erro ao gerar PIX: {e}")
            bot.send_message(call.message.chat.id, f"❌ Erro de conexão com o meio de pagamento.")

@bot.message_handler(content_types=['photo', 'video'])
def get_file_id(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if message.photo:
        file_id = message.photo[-1].file_id
        bot.reply_to(message, f"📸 *ID da Foto:*\n`{file_id}`", parse_mode="Markdown")
    elif message.video:
        file_id = message.video.file_id
        bot.reply_to(message, f"🎥 *ID do Vídeo:*\n`{file_id}`", parse_mode="Markdown")
