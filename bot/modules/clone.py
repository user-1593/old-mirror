from telegram.ext import CommandHandler
from bot.helper.mirror_utils.upload_utils import gdriveTools
from bot.helper.telegram_helper.message_utils import *
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot import dispatcher, LOGGER, CLONE_LIMIT, STOP_DUPLICATE, download_dict, download_dict_lock, Interval
from bot.helper.ext_utils.bot_utils import get_readable_file_size, check_limit, is_gdtot_link, is_gdrive_link
from bot.helper.mirror_utils.download_utils.direct_link_generator import gdtot
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
import random
import string


def cloneNode(update, context):
    args = update.message.text.split(" ", maxsplit=1)
    link = ''
    if len(args) > 1:
        link = args[1]
    is_gdtot = is_gdtot_link(link)
    if is_gdtot:
        try:
            msg = sendMessage(f"Processing: <code>{link}</code>", context.bot, update)
            link = gdtot(link)
            deleteMessage(context.bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(context.bot, msg)
            return sendMessage(str(e), context.bot, update.message)
    if is_gdrive_link(link):
        gd = gdriveTools.GoogleDriveHelper()
        res, size, name, files = gd.clonehelper(link)
        if res != "":
            sendMessage(res, context.bot, update)
            return
        if STOP_DUPLICATE:
            LOGGER.info(f"Checking File/Folder if already in Drive...")
            smsg, button = gd.drive_list(name)
            if smsg:
                msg3 = "𝐅𝐢𝐥𝐞/𝐅𝐨𝐥𝐝𝐞𝐫 𝐢𝐬 𝐚𝐥𝐫𝐞𝐚𝐝𝐲 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐢𝐧 𝐃𝐫𝐢𝐯𝐞.\n𝐇𝐞𝐫𝐞 𝐀𝐫𝐞 𝐓𝐡𝐞 𝐑𝐞𝐬𝐮𝐥𝐭𝐬:"
                sendMarkup(msg3, context.bot, update, button)
                return
        if CLONE_LIMIT is not None:
            result = check_limit(size, CLONE_LIMIT)
            if result:
                msg2 = f'𝐅𝐚𝐢𝐥𝐞𝐝, 𝐂𝐥𝐨𝐧𝐞 𝐥𝐢𝐦𝐢𝐭 𝐢𝐬 {CLONE_LIMIT}.\n𝐘𝐨𝐮𝐫 𝐅𝐢𝐥𝐞/𝐅𝐨𝐥𝐝𝐞𝐫 𝐬𝐢𝐳𝐞 𝐢𝐬 {get_readable_file_size(clonesize)}.'
                sendMessage(msg2, context.bot, update)
                return
        if files < 15:
            msg = sendMessage(f"𝐂𝐥𝐨𝐧𝐢𝐧𝐠: <code>{link}</code>", context.bot, update)
            result, button = gd.clone(link)
            deleteMessage(context.bot, msg)
        else:
            drive = gdriveTools.GoogleDriveHelper(name)
            gid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
            clone_status = CloneStatus(drive, size, update, gid)
            with download_dict_lock:
                download_dict[update.message.message_id] = clone_status
            sendStatusMessage(update, context.bot)
            result, button = drive.clone(link)
            with download_dict_lock:
                del download_dict[update.message.message_id]
                count = len(download_dict)
            try:
                if count == 0:
                    Interval[0].cancel()
                    del Interval[0]
                    delete_all_messages()
                else:
                    update_all_messages()
            except IndexError:
                pass
        if update.message.from_user.username:
            uname = f'@{update.message.from_user.username}'
        else:
            uname = f'<a href="tg://user?id={update.message.from_user.id}">{update.message.from_user.first_name}</a>'
        if uname is not None:
            cc = f'\n\ncc: {uname}'
            men = f'{uname} '
        if button in ("cancelled", ""):
            sendMessage(men + result, context.bot, update)
        else:
            sendMarkup(result + cc, context.bot, update, button)
    else:
        sendMessage('𝐏𝐫𝐨𝐯𝐢𝐝𝐞 𝐆-𝐃𝐫𝐢𝐯𝐞 𝐒𝐡𝐚𝐫𝐞𝐚𝐛𝐥𝐞 𝐋𝐢𝐧𝐤 𝐭𝐨 𝐂𝐥𝐨𝐧𝐞.', context.bot, update)
    if is_gdtot:
        gd.deletefile(link)
    LOGGER.info(f"Cloning Done")

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
