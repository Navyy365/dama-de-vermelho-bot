import os
from flask import Flask, request, jsonify
import telebot
import mercadopago

# 1. Carregar variáveis de ambiente (mantendo os IDs e tokens originais)
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
TOKEN_MERCADO_PAGO = os.getenv("TOKEN_MERCADO_PAGO")
GRUPO_VIP_ID = os.getenv("GRUPO_VIP_ID")
LINK_CONVITE_VIP = os.getenv("LINK_CONVITE_VIP")

# Validação inicial de segurança
if not TOKEN_TELEGRAM:
    raise ValueError("A variável de ambiente TOKEN_TELEGRAM não está configurada!")

# Inicializar o bot, o Flask e o SDK do Mercado Pago
bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=False)
app = Flask(__name__)

# Configurar SDK do Mercado Pago se o token existir
sdk = mercadopago.SDK(TOKEN_MERCADO_PAGO) if TOKEN_MERCADO_PAGO else None


@app.route("/", methods=["GET"])
def index():
    """Rota de verificação para garantir que o serviço na Render está ativo."""
    return "Dama de Vermelho Bot a funcionar a 100%!", 200


@app.route("/", methods=["POST"])
def webhook():
    """Rota que recebe os eventos (updates) enviados pelo Telegram."""
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    else:
        return "Formato inválido", 403


@app.route("/webhook-mercadopago", methods=["POST"])
def webhook_mercadopago():
    """Rota que recebe as notificações de pagamento aprovado do Mercado Pago."""
    data = request.json
    if not data:
        return "", 200

    if data.get("type") == "payment":
        payment_id = data.get("data", {}).get("id")
        
        if sdk and payment_id:
            payment_info = sdk.payment().get(payment_id)
            payment = payment_info.get("response", {})
            
            status = payment.get("status")
            external_reference = payment.get("external_reference") # ID do utilizador do Telegram
            
            if status == "approved":
                if external_reference and LINK_CONVITE_VIP:
                    try:
                        bot.send_message(
                            chat_id=external_reference,
                            text=f"Pagamento aprovado com sucesso! 🎉 Podes aceder ao grupo através deste link: {LINK_CONVITE_VIP}"
                        )
                    except Exception as e:
                        print(f"Erro ao enviar mensagem ao utilizador: {e}")

    return "", 200


@bot.message_handler(commands=['start'])
def comando_start(message):
    """Comando inicial de boas-vindas do bot."""
    nome_utilizador = message.from_user.first_name or "utilizador"
    bot.reply_to(
        message, 
        f"Olá, {nome_utilizador}! O bot está online e pronto a ajudar."
    )


@bot.message_handler(commands=['ping'])
def comando_ping(message):
    """Comando simples para testar a resposta do bot."""
    bot.reply_to(message, "Pong! 🚀 O sistema está a funcionar perfeitamente.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
