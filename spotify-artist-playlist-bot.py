import sys
import csv
import math
import spotipy
import spotipy.util as util
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("playlist-debug.log", mode='w'),
        logging.StreamHandler()
    ]
)

# CHANGE THESE
# Get your Client ID + Secret here: https://developer.spotify.com/dashboard/applications
client_id = ''
client_secret = ''
redirect_uri = 'http://localhost:8000'
playlist_name = 'SB: Artist Top Hits'

scope = 'user-follow-read playlist-modify-public'
batchSize = 100 # Number of tracks to add to playlist at once. Spotify max is 100.

# Read stdin for username and prompt for auth.
if len(sys.argv) > 1:
    username = sys.argv[1]
else:
    print("Usage: %s username" % (sys.argv[0],))
    sys.exit()

token = util.prompt_for_user_token(username, scope, 
    client_id=client_id, 
    client_secret=client_secret,
    redirect_uri=redirect_uri)

if token:
    sp = spotipy.Spotify(auth=token)
    
    # Check if an old version of our playlist exists and unfollow it so we start fresh.
    playlists = sp.user_playlists(username)
    for play in playlists['items']:
        if play['name'] == playlist_name:
            logging.info("Found previously generated playlist. Unfollowing to start fresh.")
            sp.user_playlist_unfollow(username, play['id'])
            break

    logging.info("Creating playlist %s", playlist_name)
    playlist = sp.user_playlist_create(username, playlist_name, public=True)

    # Get users followed artists.
    artistIds = list()
    after = None
    followed = sp.current_user_followed_artists(limit=50, after=after)
    while (followed['artists']['cursors']['after']):
        followed = sp.current_user_followed_artists(limit=50, after=after)
        items = followed['artists']['items']
        for artist in items:
            logging.info("Found artist: %s with id: %s", artist['name'], artist['id'])
            artistIds.append(artist['id'])       
        after = followed['artists']['cursors']['after']

    artistIds.reverse()

    # Determine number of songs to retrieve per artist, given max playlist tracks is 10,000
    numberOfArtists = len(artistIds)
    logging.info("Found %s followed artists.", numberOfArtists)
    tracksToGet = math.floor(10000/numberOfArtists) 
    logging.info("Retrieving each artists top %s tracks to add to playlist.", tracksToGet)
    leftover = 10000 % numberOfArtists
    numberOfBiggerBatches = math.floor(leftover / (tracksToGet + 1))
    logging.info("%s artists will get top %s tracks.", numberOfBiggerBatches, tracksToGet + 1)
    curBatch = 0
    extras = 0 # Some artists have <10 top tracks, so we can add any extras to get from other artists.


    # Get top X tracks and add to new playlist.
    trackBatch = list()
    for id in artistIds:
        logging.debug("Getting top tracks for artist id: %s", id)
        limit = tracksToGet
        res = sp.artist_top_tracks(id)
        tracksFound = len(res['tracks'])

        if tracksFound > 0:
            if curBatch <= numberOfBiggerBatches:
                limit += 1
                curBatch += 1

            if tracksFound < limit:
                toAdd = limit - tracksFound
                extras += toAdd
                limit = tracksFound
                curBatch -= 1 # Don't waste a big batch on an artist with not enough tracks.
                logging.info('Artist had only %s top tracks. Added %s extras for a current total of %s. Getting only %s tracks from current artist.', tracksFound, toAdd, extras, limit)
            elif extras > 0:
                additionalWanted = 10 - limit
                additionalActual = min(additionalWanted, extras)
                extras -= additionalActual
                limit += additionalActual
                logging.info('Getting %s additional tracks for artist for a total of %s. There are %s extra tracks banked.', additionalActual, limit, extras)       

            for track in res['tracks'][:limit]:
                trackBatch.append(track['id'])

    # Create the batch to send to the API
    batch = list()
    ctr = 0 
    for id in trackBatch:
        batch.append(id)

        if (ctr % batchSize) == 0:  
            msg = 'Sending batch: {0}'.format(' '.join(batch))  
            logging.info(msg)
            sp.user_playlist_add_tracks(username,playlist['id'],batch)

            # Erase the batch for next iter.    
            batch.clear()

        ctr += 1
else:
    logging.error('Error getting token for {0}'.format(username))