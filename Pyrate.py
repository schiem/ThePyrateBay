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

import urllib2
import time
import datetime

import libtorrent as lt
from tpb import TPB
from tpb import CATEGORIES, ORDERS
from bs4 import BeautifulSoup

import configparser
import os

SETTINGS_PATH = "settings.ini"

'''
A function to search imdb. 
Parameter: date_range
    A string in the format of 'YYYY-MM-DD YYYY-MM-DD'
Parameter: rating
    Either asc or desc as a string.  Other values will
    return an error
Return: Raw HTML returned by searching IMDB.
'''
def search(date_range, rating):
    #various arguments in the advanced search
    url = get_setting("url")
    release = 'release_date={0}'.format(date_range)
    title = 'title?at=0'
    language = 'languages=en'
    title_type = 'title_type=feature'
    sort = 'sort=user_rating,{0}'.format(rating)
    votes = 'num_votes=100,'
    #the url to query imdb
    search_url = '{0}/{1}&{2}&{3}&{4}&{5}&{6}'.format(url, title, language, votes, release, sort, title_type)
    results = urllib2.urlopen(search_url)
    print "Searching using url : {0}".format(search_url)
    return results.read()


'''
Parse the raw IMDB html to find the movie titles in the list.
Parameter: imdb_html
    The raw html from an imdb search
Return:
    A list of movie titles
'''
def get_titles_and_ratings(imdb_html):
    bs = BeautifulSoup(imdb_html)
    links = {}
    for title in bs.find_all('td', {'class' : 'title'}):
         links[title.find('a').text] = float(title.find('span', {'class' : 'value'}).text)
    print links
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
    pirate = TPB('https://thepiratebay.org')
    search = pirate.search(title, category=CATEGORIES.VIDEO.MOVIES).order(ORDERS.SEEDERS.DES)
    for torrent in search:
        result = torrent
        break; 
    if(result == None or result.seeders < int(get_setting("seeders"))):
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

'''
If settings.conf doesn't exist, create it and fill it with user input.
If it does exist, iterate through it and fill the settings.  If there are
extraneous settings, remove them.  If settings are missing, prompt the user
for them.
'''
def configure():
    if not os.path.exists(get_setting("save")):
        os.makedirs(get_setting("save"))
        print "Torrents directory not found, creating..."

'''
Load in the settings.ini file.
Return:
    A configparser object containing settings.ini.
'''
def load_settings():
    settings = configparser.ConfigParser()
    settings.read(SETTINGS_PATH)
    settings = settings["Search"]
    return settings

def get_setting(setting):
    return load_settings()[setting]

def subtract_years(date, years):
    dates = date.split(" ")
    new_dates = []
    for d in dates:
        new_dates.append(str(int(d[0:4]) - years) + d[4:])
    return " ".join(new_dates)

def keys_from_dict(_dict, number, order):
    keys = []
    for i in range(number):
        if(order == 'asc'):
            _key = max(_dict.iterkeys(), key=(lambda key: _dict[key]))
        elif(order  == 'desc'):
            _key = min(_dict.iterkeys(), key=(lambda key: _dict[key]))

        else:
            return []
        _dict.pop(_key)
        keys.append(_key)
    return keys

def get_movies():
    date = get_setting("dates")
    if(date == 'None'):
        #if no date is selected, then the date used should be today
        date = str(datetime.date.today())
        date = "{0} {1}".format(date, date)

    years = int(get_setting("years"))
    good_html = []
    bad_html = []
    
    good_results = {}
    bad_results = {}
    
    for i in range(years): 
        print date, i
        search_date = subtract_years(date, i+1)
        good_html = search(search_date, 'asc')
        bad_html = search(search_date, 'desc')

        
        good_results.update(get_titles_and_ratings(good_html))
        bad_results.update(get_titles_and_ratings(bad_html))
    to_download = keys_from_dict(good_results, int(get_setting("good")), 'asc')
    to_download += keys_from_dict(bad_results, int(get_setting("bad")), 'desc')
    return to_download 
    

if __name__ == "__main__":
    configure()
    if(get_setting("time") == "None"):
        #get a list of movies we want
        movie_list = get_movies()
        torrents = []

        #Try to find torrents for those movies
        for movie in movie_list:
            print "Attempting to get torrent for {0}".format(movie)
            torrent = get_torrent(movie)
            if(torrent):
                print("Success!")
                torrents.append(torrent)
            else:
                print("Sorry, no torrent found.")
        
        #if no torrents were found, stop
        if(len(torrents) == 0):
            print("Sorry, none of the movies were found on the piratebay...exiting quietly.")
        
        #otherwise, download the torrents
        else:
            for torrent in torrents:
                download_magnet(torrent.magnet_link)

