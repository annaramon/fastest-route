from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import igo
import time

# Constant with the token acces
TOKEN = open('token.txt').read().strip()

# Images names
POSITION_IMAGE = 'my_position.png'
PATH_IMAGE = 'shortest_path.png'

# Necessary objects for working with telegram
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher


def start(update, context):
    """Downloads the graph if it's not already downloaded and sends a message to the user saying hello"""

    # Initializes the Igo  module
    igo.start_system()

    # At the begining, we'll use the real ubication, though we'll keep track
    # which poisitoin is being used, as the user can fake the position with the
    # /pos function.
    context.user_data['use_real_position'] = True
    context.user_data['real_position'] = -1  # At the begining there's no register of any location so we initize the position with -1
    context.user_data['false_position'] = -1  # At the begining there's no register of any location so we initize the position with -1

    # As congestions are modified every 5 minutes,and the igraph needs congestions
    # and highways to be built,  we'll keep track of the time that has passsed since
    # the last time we've downloaded them, so we do not have to calculate the igraph more
    # times than necessary.
    context.user_data['last_time_refresh'] = -1

    message = "Hola! Sóc el bot igo!"  # message sent to the user

    # Show the MessageHandler
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message)


# Shows a list of the functions that the user can use
def help(update, context):
    """Sends to the user the commands that he can ask for"""

    message = '''Sóc un bot amb comandes:

        /start:		Inicialitza el bot.
        /help:		Mostra les comandes que es poden executar.
        /author:	Mostra l'autor d'aquest bot.
        /go desti:	Mostra una imatge amb el camí més ràpid desde l'ubicació actual fins el destí indicat
        /where:		Mostra una imatge amb la teva posició actual.
        /pos:		Falsejar la teva possicio
        /unpos:		Utilitzar la posició real
    '''

    # Show the message
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message)


def author(update, context):
    """Sends a message with the author's names"""

    message = "Els meus autors són l'Anna i l'Adrià"

    # Command for sending the message to the user
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message)


def go(update, context):
    """ Shows an image with the fastest path from the user's departure point (origen) to the arrival point, destination,
    the departure point (origin) can be a fake location or the user's current location"""
    # Transform the destination given as a text message to a point -->coordinates
    dest_lat, dest_lon = _get_coords_from_message(update, context, 2)

    # If 5 minutes have gone by since the last calculation of the igraph, its time
    # to calculate it again, as the congestions will have already been updated.
    current_time = time.time()  # We'll use the time.time() function to tell us the current time

    # If its the firts time the user is using the go function, we'll need to calculate the igraph
    # if more than 5 minutes (300 seconds) have gone by, we'll need to calculate the igraph again
    if context.user_data['last_time_refresh'] == -1 or current_time - context.user_data['last_time_refresh'] > 300:
        need_igraph = True
        context.user_data['last_time_refresh'] = current_time  # We'll save the time to know when the 5 minutes will have passed again
    else:
        need_igraph = False  # If the 5 minutes have not gone by, the igraph is still updated and saved in the pickle, so there is no need to spend time calculating it again

    if context.user_data['use_real_position']:  # Use the real ubication as the origin point.

        if context.user_data['real_position'] == -1:  # There is not a position saved
            result = 0
        else:  # We'll use the saved location as start point
            org_lat, org_lon = context.user_data['real_position']
            result = igo.shortest_path((org_lon, org_lat), (dest_lon, dest_lat), need_igraph, PATH_IMAGE)

    else:  # We'll use the false position as start point
        org_lat, org_lon = context.user_data['false_position']
        result = igo.shortest_path((org_lon, org_lat), (dest_lon, dest_lat), need_igraph, PATH_IMAGE)

    # We'll edcide what to show in the users sreen depending on the result of the previous operation
    if result is None:  # We've found a path between the two locations
        context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=open(PATH_IMAGE, 'rb'))

    elif result == 0:  # The user has not sent a origin position
        context.user_data['last_time_refresh'] = -1
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Envia'm la teva localització o indica'n alguna amb la comanda /pos!")

    elif result == -1:  # We have not been able to fiind a path between the two locations
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No s'ha pogut trobar un cami entre l'origen i destí indicats")


def where(update, context):
    """It shows the last given ubication, if the user hasn't sent any ubication aks for one"""

    if context.user_data['use_real_position'] is True:  # We have to show the real position

        if context.user_data['real_position'] == -1:  # We don't have any location registed
            # We ask for the users location
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Envia'm la teva localització o indica'n alguna amb la comanda /pos!")

        # We already have the real registered location
        else:
            # Take the location
            lat, lon = context.user_data['real_position']
            # Show the location using the function defined in the igo module
            igo.show_position(lon, lat, POSITION_IMAGE)
            # Send the image
            context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=open(POSITION_IMAGE, 'rb'))

    else:  # We need to show te false location
        lat, lon = context.user_data['false_position']
        igo.show_position(lon, lat, POSITION_IMAGE)

        context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=open(POSITION_IMAGE, 'rb'))


def get_position(update, context):
    """Shows the user's current ubication"""

    # Code for sharing the user's live location
    message = update.edited_message if update.edited_message else update.message

    # Saves the position in the user_data
    lat, lon = update.message.location.latitude, update.message.location.longitude
    context.user_data['real_position'] = (lat, lon)


def pos(update, context):
    """The user sends an ubication, which will be use as a departure point. It's like a fake current location for the algorism"""
    # Get the coordinates from the position that the user has sent
    # IMPORTANT: The coordinates has to be given first latitude and then longitude
    lat, lon = _get_coords_from_message(update, context, 3)

    # Keep the position in the user_data, update it
    context.user_data['use_real_position'] = False
    context.user_data['false_position'] = (lat, lon)


def unpos(update, context):
    """We can stop using the false location and the user can still look for paths with his real location"""
    context.user_data['use_real_position'] = True


def _get_coords_from_message(update, context, comand_size):
    """The locations can be given as a text, name of the place, or by coordinates"""
    # Location given as text --> string type
    if update.message.text[comand_size+2] < '0' or update.message.text[comand_size+2] > '9':
        direction = update.message.text[comand_size+2:]
        return igo.translate_direction(direction)

    # Location given as coordinates
    else:
        # The location has a number --> coordinates
        lat = context.args[0]  # First number represents latitude
        lon = context.args[1]  # Second number represents longitude
        return (float(lat), float(lon))  # Returns the latitude and longitude arrival point


# Guides the bot: when the user send a a command, it guides the bot for executing the correct function
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', help))
dispatcher.add_handler(CommandHandler('author', author))
dispatcher.add_handler(CommandHandler('go', go))
dispatcher.add_handler(CommandHandler('where', where))
dispatcher.add_handler(MessageHandler(Filters.location, get_position))
dispatcher.add_handler(CommandHandler('pos', pos))
dispatcher.add_handler(CommandHandler('unpos', unpos))


# Start bot
updater.start_polling()
