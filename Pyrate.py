###############################################
#  Search IMDB for the top movies in a given time
#  and download it from the pirate bay.  
#
#  v 0.1
#  Michael Yoder
#
#  External Reqs:  BeautifulSoup (4) 
#                  ThePirateBay
#                  LibTorrent
#  Standard Reqs:  urllib2
#                  time
#                  datetime
#                  configparser
#                  os
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


############### IMDB Functions ######################

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
    votes = 'num_votes=50,'
    #the url to query imdb
    search_url = '{0}/{1}&{2}&{3}&{4}&{5}&{6}'.format(url, title, language, votes, release, sort, title_type)
    results = urllib2.urlopen(search_url)
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
    return links


############### ThePirateBay Functions ######################
'''
Searches ThePirateBay for a given title in the category MOVIES.
Parameter: title
    The title to search for.
Return:
    The search result with the most seeders.  If no results are
    found or if there aren't enough seeders, return None.
'''
def search_torrent(title):
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

############### Torrenting Functions ######################
'''
Convert a magnet file to a torrent and download the torrent associated with it.
Parameter: magnet
    The magnet link to use.
Return:
    None.
'''
def download_magnet(magnet):
    ses = lt.session()

    params = { 'save_path': str(get_setting("save")), \
        'duplicate_is_error' : True }
    #add the magnet
    
    h = lt.add_magnet_uri(ses, magnet, params)

    #get the metadata from the magnet
    while (not h.has_metadata()):
        quiet_print("Receiving metadata...")
        time.sleep(1)
    
    #download the torrent
    while (not h.is_seed()):
        s = h.status()
        quiet_print('%.2f%% complete (down: %.1f kb/s up: %.1f kB/s peers: %d) %s' % \
                (s.progress * 100, s.download_rate / 1000, s.upload_rate / 1000, \
                s.num_peers, s.state))
        time.sleep(1)

'''
Attempt to get a find a certain number of torrents from The Pirate Bay from a list
of titles. The function will continue to search until it has either found the supplied
number of torrents or reached the end of the list.
Parameter: movies
    The list of movie titles to search for.
Parameter: number
    The number of torrents to find.
Return:
    A list of torrent objects.
'''
def get_torrents(movies, number):
    torrents = []
    i = 0
    while i<len(movies) and len(torrents) < number:
        quiet_print("Attempting to get torrent for {0}".format(movies[i]))
        torrent = search_torrent(movies[i])
        if(torrent):
            quiet_print("Found a torrent!")
            torrents.append(torrent)
        else:
            quiet_print("No torrent found...")
        i += 1
    return torrents


############### Settings Functions ######################

'''
If settings.conf doesn't exist, create it and fill it with user input.
If it does exist, iterate through it and fill the settings.  If there are
extraneous settings, remove them.  If settings are missing, prompt the user
for them.
'''
def configure():
    if not os.path.exists(get_setting("save")):
        os.makedirs(get_setting("save"))
        quiet_print("Torrents directory not found, creating...")

'''
Doesn't print if it's going to be run in the background.
'''
def quiet_print(string):
    if(get_setting(time) == "None"):
        print string

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

'''
Gets a setting from the settings.ini file.
Parameter: setting
    A string of the setting to get.
Return:
    The value of the setting in the file. Will raise
    a KeyError if no setting is found.
'''
def get_setting(setting):
    return load_settings()[setting]

'''
Subtracts a specified number of years from a date given in the format
YYYY-MM-DD,YYYY-MM-DD
Parameter: date
    A string representing the date.
Parameter: years
    The number of years to subtract.
Return:
    A string representing the new date in the format YYYY-MM-DD,YYYY-MM-DD
'''
def subtract_years(date, years):
    dates = date.split(",")
    new_dates = []
    for d in dates:
        new_dates.append(str(int(d[0:4]) - years) + d[4:])
    return ",".join(new_dates)

'''
Moves the keys of a dictionary to a list based on the numerical value
in the dictionary.  Assumes that the values in the dictionary are ints.
Parameter: _dict
    The dictionary to iterate through
Parameter: order
    Whether to sort by highest or lowerst value.
Return:
    An ordered list containing the keys of the dictionary.
'''
def sort_keys_by_value(_dict, order):
    keys = []
    for i in range(len(_dict)):
        if(order == 'asc'):
            _key = max(_dict.iterkeys(), key=(lambda key: _dict[key]))
        elif(order  == 'desc'):
            _key = min(_dict.iterkeys(), key=(lambda key: _dict[key]))

        else:
            return []
        _dict.pop(_key)
        keys.append(_key)
    return keys




############### Main Functions ##########################

'''
Generate a list of all the best and worst movies in a given range of years.
Return:
    Two lists of the best and worst movies ordered by rating.
'''
def get_movies():
    date = get_setting("dates")
    if(date == 'None'):
        #if no date is selected, then the date used should be today
        date = str(datetime.date.today())
        date = "{0},{1}".format(date, date)

    #get the number of years to search
    years = int(get_setting("years"))
    
    #set up empty variables
    good_html = []
    bad_html = []
    
    good_results = {}
    bad_results = {}
    
    #get the search results for the specified date for the number of 
    #years specified
    for i in range(years): 
        #get the new date to search for
        search_date = subtract_years(date, i+1)
        
        #get the raw html from imdb
        good_html = search(search_date, 'asc')
        bad_html = search(search_date, 'desc')
        
        #translate the raw html to titles and ratings
        good_results.update(get_titles_and_ratings(good_html))
        bad_results.update(get_titles_and_ratings(bad_html))
    
    #turn the titles and ratings into a sorted list of titles
    good_movies = sort_keys_by_value(good_results, 'asc')
    bad_movies = sort_keys_by_value(bad_results, 'desc')
    return good_movies, bad_movies
    
'''
The main function.  Searches IMDB for movies in the specified date
range, then attempts to download them from ThePirateBay.
'''
def run():
    #get a list of movies we want
    good_movies, bad_movies = get_movies()
    torrents = []

    #Try to find torrents for those movies
    quiet_print("Getting good movies...")
    to_download = get_torrents(good_movies, int(get_setting("good")))
    quiet_print("Getting bad movies...")
    to_download += get_torrents(bad_movies, int(get_setting("bad")))
    
    #remove duplicates
    to_download = list(set(to_download))
    
    #if no torrents were found, stop
    if(len(to_download) == 0):
        quiet_print("Sorry, none of the movies were found on the piratebay...exiting quietly.")

    #otherwise, download the torrents (ensuring that we don't download duplicates)
    else:
        for torrent in to_download:
            download_magnet(torrent.magnet_link)


if __name__ == "__main__":
    configure()
    if(get_setting("time") == "None"):
        run()
