###############################################
#  Search IMDB for the top movies in a given time
#  and download it from the pirate bay.  
#
#  v 0.1
#  Michael Yoder
#
#  Reqs:   
#         ThePirateBay
#         LibTorrent
################################################

import libtorrent as lt
from tpb import TPB
from tpb import CATEGORIES, ORDERS

from bs4 import BeautifulSoup

import urllib2
import time
import os

pirate = TPB('https://thepiratebay.org')
IMDB_search = 'http://akas.imdb.com/search'
MIN_SEEDERS = 20
SAVE_PATH = "./torrents/"

'''
A function to search imdb. 
Parameter: date_range
    A list of two strings in the format YYYY-MM-DD
Parameter: rating
    Either asc or desc as a string.  Other values will
    return an error
Return: Raw HTML returned by searching IMDB.
'''
def search(date_range, rating):
    #various arguments in the advanced search
    release = 'release_date={0},{1}'.format(date_range[0], date_range[1])
    title = 'title?at=0'
    language = 'languages=en'
    title_type = 'title_type=feature'
    sort = 'sort=user_rating,{0}'.format(rating)
    votes = 'num_votes=100,'

    #the url to query imdb
    search_url = '{0}/{1}&{2}&{3}&{4}&{5}&{6}'.format(IMDB_search, title, language, votes, release, sort, title_type)
    results = urllib2.urlopen(search_url)
    print search_url
    return results.read()


'''
Parse the raw IMDB html to find the movie titles in the list.
Parameter: imdb_html
    The raw html from an imdb search
Return:
    A list of movie titles
'''
def get_titles(imdb_html):
    bs = BeautifulSoup(imdb_html)
    links = []
    for title in bs.find_all('td', {'class' : 'title'}):
         links.append(title.find('a').text)
    return links

'''
Searches ThePirateBay for a given title in the category MOVIES.
Parameter: title
    The title to search for.
Return:
    The search result with the most seeders.  If no results are
    found or if there aren't enough seeders, return None.
'''
def get_torrent(title):
    result = None
    search = pirate.search(title, category=CATEGORIES.VIDEO.MOVIES).order(ORDERS.SEEDERS.DES)
    for torrent in search:
        result = torrent
        break; 
    if(result == None or result.seeders < MIN_SEEDERS):
        return None
    else:
        return result

'''
Use libtorrent to download the data from a torrent file.
Parameter: torrent
    The file path of the torrent to download.
Return:
    None.
'''
def download_torrent(torrent):
    
    #create a new libtorrent session
    ses = lt.session()
    ses.listen_on(6881, 6891)

    #open the torrent file
    e = lt.bdecode(open(torrent, 'rb').read())
    info = lt.torrent_info(e)

    params = { 'save_path': SAVE_PATH, \
        'storage_mode': lt.storage_mode_t.storage_mode_sparse, \
        'ti': info }

    #add the torrent to the session
    h = ses.add_torrent(params)

    #if we're not seeding yet...
    while (not h.is_seed()):
        s = h.status()
        print('%.2f%% complete (down: %.1f kb/s up: %.1f kB/s peers: %d) %s' % \
                (s.progress * 100, s.download_rate / 1000, s.upload_rate / 1000, \
                s.num_peers, s.state))

        time.sleep(1)

'''
Get a torrent file from ThePirateBay.
Parameter: torrent_url
    The path to the torrent file.
Return:
    The file name that the torrent was saved under.
'''
def download_torrent_file(torrent_url):
    file_name = torrent_url.split('/')[-1]
    u = urllib2.urlopen(url)
    f = open(file_name, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (file_name, file_size)

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        print(status)

    f.close()
    return file_name

'''
Convert a magnet file to a torrent and download the torrent associated with it.
Parameter: magnet
    The magnet link to use.
Return:
    None.
'''
def download_magnet(magnet):
    ses = lt.session()


    params = { 'save_path': SAVE_PATH, \
        'duplicate_is_error' : True }
    #add the magnet
    h = lt.add_magnet_uri(ses, magnet, params)

    #get the metadata from the magnet
    while (not h.has_metadata()):
        print "Receiving metadata..."
        time.sleep(1)
    
    #download the torrent
    while (not h.is_seed()):
        s = h.status()
        print('%.2f%% complete (down: %.1f kb/s up: %.1f kB/s peers: %d) %s' % \
                (s.progress * 100, s.download_rate / 1000, s.upload_rate / 1000, \
                s.num_peers, s.state))
        time.sleep(1)

def configure():
   if not os.path.exists(SAVE_PATH):
       os.makedirs(SAVE_PATH)
       print "Torrents directory not found, creating..."

if __name__ == "__main__":
    configure()
    imdb_results = search(['2011-02-14', '2013-04-12'], 'desc')
    movie_titles = get_titles(imdb_results)
    i = 0
    torrent = None
    while(torrent == None):
        print "Attempting to get torrent {0}".format(movie_titles[i])
        torrent = get_torrent(movie_titles[i])
        i += 1
    print torrent.seeders
    download_magnet(torrent.magnet_link)
