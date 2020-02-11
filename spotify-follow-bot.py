import sys
import csv
import spotipy
import spotipy.util as util
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log", mode='w'),
        logging.StreamHandler()
    ]
)

# CHANGE THESE
# Get your Client ID + Secret here: https://developer.spotify.com/dashboard/applications
client_id = 'YOUR-ID-HERE'
client_secret = 'YOUR-SECRET-HERE'
redirect_uri = 'http://localhost:8000'
artist_csv_path = 'artists.csv'

scope = 'user-follow-read user-follow-modify'
batchSize = 50 # Number of artists to follow per API call. Spotify max is 50.

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

    # Load CSV of artitsts to follow.
    with open(artist_csv_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')

        foundArtistIDs = set()
        for row in reader:
            for a in row:
                a = a.strip()
                logging.info('Searching for: "{0}"'.format(a))
                results = sp.search(q='artist:"' + a + '"', type='artist', limit=50)
                items = results['artists']['items']
            
                if len(items) > 0:
                    exactFound = False
                    for artist in items:                    
                        if artist['name'].lower() == a.lower():
                            msg = 'Exact match found for: {0}\n\tartist: {1}\n\tid: {2}'.format(a, artist['name'], artist['id'])
                            logging.info(msg) 
                            
                            foundArtistIDs.add(artist['id'])
                            exactFound = True
                            break
                        else:
                            logging.warning('Artist returned was: "{0}"'.format(artist['name']))
                            continue

                    if not exactFound:
                        logging.error('Could not find exact match for: "{0}"'.format(a))    
                else:
                    logging.warning('No results for: "{0}"'.format(a))
        
        # Create the batch to send to the API
        batch = list()
        ctr = 0 
        for id in foundArtistIDs:
            batch.append(id)

            if (ctr % batchSize) == 0:  
                msg = 'Sending batch: {0}'.format(' '.join(batch))  
                logging.info(msg)
                sp.user_follow_artists(batch)

                # Erase the batch for next iter.    
                batch.clear()

            ctr += 1
        
        if (len(batch) > 0):
            msg = 'Sending remaining batch of < {0} items: {1}'.format(batchSize, ' '.join(batch))
            logging.info(msg)
            sp.user_follow_artists(batch)
else:
    logging.error('Error getting token for {0}'.format(username))