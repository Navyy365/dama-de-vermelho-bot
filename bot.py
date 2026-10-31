import os
from flask import Flask, request
import telebot

# 1. Carregar variáveis de ambiente com segurança
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
TOKEN_MERCADO_PAGO = os.getenv("TOKEN_MERCADO_PAGO")
GRUPO_VIP_ID = os.getenv("GRUPO_VIP_ID")
LINK_CONVITE_VIP = os.getenv("LINK_CONVITE_VIP")
CHAVE_SECRETA_CRON = os.getenv("CHAVE_SECRETA_CRON")

# Validação inicial do token do Telegram
if not TOKEN_TELEGRAM:
    raise ValueError("A variável de ambiente TOKEN_TELEGRAM não está configurada!")

# Inicializar o bot e a aplicação Flask
bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=False)
app = Flask(__name__)


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


@bot.message_handler(commands=['start'])
def comando_start(message):
    """Comando inicial de boas-vindas do bot."""
    nome_utilizador = message.from_user.first_name or "utilizador"
    bot.reply_to(
        message, 
        f"Olá, {nome_utilizador}! O bot foi reiniciado com sucesso e está pronto a operar."
    )


@bot.message_handler(commands=['ping'])
def comando_ping(message):
    """Comando simples para testar se o bot está vivo."""
    bot.reply_to(message, "Pong! 🚀 O sistema está online.")


if __name__ == "__main__":
    # Execução local para testes (na Render o Gunicorn assume o controlo)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
