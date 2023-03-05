import logging
import aiohttp
from environs import Env
from aiogram import Bot, Dispatcher, md
from aiogram.types import Message, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart


OPENAPI_URL = "https://ark0f.github.io/tg-bot-api/openapi.json"

LOCAL_API_DATA = F"""
{md.link(
    value='Using a Local Bot API Server', 
    link='https://core.telegram.org/bots/api/#using-a-local-bot-api-server')
}

The Bot API server source code is available at {md.link(
    value='telegram-bot-api',
    link='https://github.com/tdlib/telegram-bot-api')}. \
You can run it locally and send the requests to your own server instead of \
{md.code('https://api.telegram.org.')} \
If you switch to a local Bot API server, your bot will be able to:


> Download files without a size limit.
> Upload files up to 2000 MB.
> Upload files using their local path and {md.link(
    value='the file URI scheme', 
    link='https://en.wikipedia.org/wiki/File_URI_scheme')}.
> Use an HTTP URL for the webhook.
> Use any local IP address for the webhook.
> Use any port for the webhook.
> Set max\_webhook\_connections up to 100000.
> Receive the absolute local path as a value of the file\_path field without the need to\
download the file after a {md.link(
    value='getFile',
    link='https://core.telegram.org/bots/api/#getfile')} request.

{md.link(
    value='Do I need a Local Bot API Server',
    link='https://core.telegram.org/bots/api/#do-i-need-a-local-bot-api-server'
)}

The majority of bots will be OK with the default configuration, running on our servers. \
But if you feel that you need one of {md.link(
        value='these features',
        link='https://core.telegram.org/bots/api/#using-a-local-bot-api-server')}, \
you're welcome to switch to your own at any time.

"""


def parse_ref(ref: str):
    if ref:
        t_ = ref.removeprefix("#/components/schemas/")
        return md.link(t_, f"https://core.telegram.org/bots/api/#{t_}")


async def get_api():
    async with aiohttp.ClientSession() as client:
        return await (await client.get(OPENAPI_URL)).json()


class TelegramAgent:
    def __init__(self) -> None:
        logging.basicConfig(level=logging.INFO)
        self.env = Env()
        self.env.read_env()
        self.bot = Bot(self.env("TELEGRAM_BOT_TOKEN"))
        self.dp = Dispatcher()
        self.api = {}
        self.log = logging.getLogger(__package__)
        self.aio = logging.getLogger("aiogram").setLevel(level=logging.WARNING)
        # handlers
        self.dp.startup.register(self.startup)
        self.dp.message.register(self.handle_start, CommandStart())
        self.dp.inline_query.register(self.handle_inline_query)

    
    def run_polling(self):
        self.dp.run_polling(self.bot)

    async def startup(self):
        await self.bot.delete_webhook(drop_pending_updates=True)
        self.api = await get_api()
        self.log.info("Handle startup")

    async def handle_start(self, message: Message):
        if message.from_user:
            self.log.info(
                "Handle /start from %s(%d|@%s)",
                message.from_user.first_name, 
                message.from_user.id,
                message.from_user.username
            )
        await message.answer(
            "Hello i inline bot to get info about Telegram Bot API\nContact: @arwichok",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Search: '/sendmessage'", 
                                     switch_inline_query_current_chat="/sendmessage")
            ]])
        )

    async def handle_inline_query(self, iq: InlineQuery):
        self.log.info("Handle iq: %s from %s(%d|@%s)", 
                      iq.query, 
                      iq.from_user.first_name, 
                      iq.from_user.id, 
                      iq.from_user.username)
        results = []
        query = iq.query
        for method, path in self.api.get("paths").items():
            if query.casefold() in method.casefold():
                desc = path["post"]["description"]
                url = path["post"]["externalDocs"]["url"]
                text = f"{md.link(method, url)} - {desc}\n\n"
                if request := path["post"].get("requestBody"):
                    content = request["content"]
                    if ((schema := content.get("application/x-www-form-urlencoded")) or\
                        (schema := content.get("multipart/form-data")) or \
                        (schema := content.get("application/json"))
                    ):
                        for pname, prop in schema["schema"]["properties"].items():
                            text += md.code(pname)

                            if p := prop.get("type"):
                                text += f": {md.code(p)}"
                            elif p := prop.get("anyOf"):
                                text += ": " + "|".join(
                                    parse_ref(pp.get("$ref")) or md.code(pp.get("type"))
                                    for pp in p)
                            text += "\n"
                result = path["post"]["responses"]["200"]["content"]\
                    ["application/json"]["schema"]["properties"]["result"]
                response = md.code("Any")
                if t_ := result.get("$ref"):
                    response = parse_ref(t_)
                elif t_ := result.get("type"):
                    if t_ == "array":
                        response = "|".join([
                            parse_ref(t) if i == "$ref" else md.code(t)
                            for i, t in result.get("items").items()
                        ])
                text += f"\n->{response}"

                results.append(InlineQueryResultArticle(
                    id=method,
                    title=method,
                    description=desc,
                    input_message_content=InputTextMessageContent(
                        parse_mode="Markdown",
                        message_text=text,
                        disable_web_page_preview=True
                    )
                ))
        for name, comp in self.api["components"]["schemas"].items():
            if query.casefold() in name.casefold() and name != "Error":
                desc = comp["description"]
                url = comp["externalDocs"]["url"]
                text = f"{md.link(name, url)} - {desc}\n\n"
                if properties := comp.get("properties"):
                    for pname, prop in properties.items():
                        p = md.code(pname)
                        pt = md.code("Any")
                        if _pt := prop.get("type"):
                            pt = md.code(_pt)
                        elif _pt := prop.get("$ref"):
                            pt = parse_ref(_pt)
                        text += f"{p}: {pt}\n"
                
                results.append(InlineQueryResultArticle(
                    id=name,
                    title=name,
                    description=desc,
                    input_message_content=InputTextMessageContent(
                        parse_mode="Markdown",
                        message_text=text,
                        disable_web_page_preview=True
                    )
                ))
        if iq.query.casefold() in "Using a Local Bot API Server".casefold():
            results.append(InlineQueryResultArticle(
                id="localapi",
                title="Using a Local Bot API Server",
                input_message_content=InputTextMessageContent(
                    parse_mode="Markdown",
                    message_text=LOCAL_API_DATA,
                    disable_web_page_preview=True
                )
            ))
        
        if iq.offset and iq.offset.isdigit():
            offset = int(iq.offset)
            results = results[offset:offset+50]
            next_offset = str(offset + 50)
        else:
            results = results[:50]
            next_offset = "50"
        await iq.answer(
            results, cache_time=1, 
            next_offset=next_offset, switch_pm_text="Help", switch_pm_parameter="iq")
