# -*- coding: utf-8 -*-
#------------------------------------------------------------
# pelisalacarta - XBMC Plugin
# Conector para streamplay
# http://blog.tvalacarta.info/plugin-xbmc/pelisalacarta/
#------------------------------------------------------------

import re

from core import jsunpack
from core import logger
from core import scrapertools

headers = [['User-Agent','Mozilla/5.0 (Windows NT 10.0; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0']]
host = "http://streamplay.to/"

def test_video_exists( page_url ):
    logger.info("pelisalacarta.streamplay test_video_exists(page_url='%s')" % page_url)
    data = scrapertools.cache_page(page_url)
    if data == "File was deleted":
        return False, "[Streamplay] El archivo no existe o ha sido borrado"

    return True, ""


def get_video_url( page_url , premium = False , user="" , password="", video_password="" ):
    logger.info("pelisalacarta.streamplay get_video_url(page_url='%s')" % page_url)
    data = scrapertools.cache_page(page_url)

    jj_encode = scrapertools.find_single_match(data, "(\w+=~\[\];.*?\)\(\)\)\(\);)")
    jj_decode = None
    jj_patron = None
    reverse = False
    substring = False
    if jj_encode:
        jj_decode = jjdecode(jj_encode)
        logger.info(jj_decode)
    if jj_decode:
        jj_patron = scrapertools.find_single_match(jj_decode, "/([^/]+)/")
    if not "(" in jj_patron:
        jj_patron = "(" + jj_patron
    if not ")" in jj_patron:
        jj_patron += ")"

    if "x72x65x76x65x72x73x65" in jj_decode:
        reverse = True
    if "x73x75x62x73x74x72x69x6Ex67" in jj_decode:
        substring = True

    matches = scrapertools.find_single_match(data, "<script type=[\"']text/javascript[\"']>(eval.*?)</script>")
    matchjs = jsunpack.unpack(matches).replace("\\", "")

    data = scrapertools.find_single_match(matchjs, "sources\s*=[^\[]*\[([^\]]+)\]")
    matches = scrapertools.find_multiple_matches(data.replace('"', "'"), "[src|file]:'([^']+)'")

    video_urls = []
    for mediaurl in matches:
        _hash = scrapertools.find_single_match(mediaurl, '\w{40,}')
        if substring:
            substring = int(scrapertools.find_single_match(jj_decode, "_\w+.\d...(\d)...;"))
            if reverse:
                _hash = _hash[:-substring]
            else:
                _hash = _hash[substring:]
        if reverse:
            mediaurl = re.sub(r'\w{40,}', _hash[::-1], mediaurl)
        filename = scrapertools.get_filename_from_url(mediaurl)[-4:]
        if mediaurl.startswith("rtmp"):
            rtmp, playpath = mediaurl.split("vod/", 1)
            mediaurl = "%s playpath=%s swfUrl=%splayer6/jwplayer.flash.swf pageUrl=%s" % (rtmp + "vod/", playpath, host, page_url)
            filename = "RTMP"
        elif "m3u8" in mediaurl:
            mediaurl += "|User-Agent=" + headers[0][1]
        elif mediaurl.endswith("/v.mp4"):
            mediaurl_flv = re.sub(r'/v.mp4$', '/v.flv', mediaurl)
            video_urls.append(["flv [streamplay]", re.sub(r'%s' % jj_patron, r'\1', mediaurl_flv)])

        video_urls.append([filename + " [streamplay]", re.sub(r'%s' % jj_patron, r'\1', mediaurl)])

    video_urls.sort(key=lambda x:x[0], reverse=True)
    for video_url in video_urls:
        logger.info(" %s - %s" % (video_url[0], video_url[1]))

    return video_urls


# Encuentra vídeos del servidor en el texto pasado
def find_videos(data):
    encontrados = set()
    devuelve = []

    # http://streamplay.to/ubhrqw1drwlx
    patronvideos = "streamplay.to/(?:embed-|)([a-z0-9]+)(?:.html|)"
    logger.info("pelisalacarta.streamplay find_videos #"+patronvideos+"#")
    matches = re.compile(patronvideos, re.DOTALL).findall(data)

    for match in matches:
        titulo = "[streamplay]"
        url = "http://streamplay.to/embed-%s.html" % match
        if url not in encontrados:
            logger.info("  url="+url)
            devuelve.append([titulo, url, 'streamplay'])
            encontrados.add(url)
        else:
            logger.info("  url duplicada="+url)

    return devuelve


def jjdecode(t):
    x = '0123456789abcdef'
    j = scrapertools.get_match(t, '^([^=]+)=')
    t = t.replace(j + '.', 'j.')

    t = re.sub(r'^.*?"\\""\+(.*?)\+"\\"".*?$', r'\1', t.replace('\\\\', '\\')) + '+""'
    t = re.sub('(\(!\[\]\+""\)\[j\._\$_\])', '"l"', t)
    t = re.sub(r'j\._\$\+', '"o"+', t)
    t = re.sub(r'j\.__\+', '"t"+', t)
    t = re.sub(r'j\._\+', '"u"+', t)

    p = scrapertools.find_multiple_matches(t, '(j\.[^\+]+\+)')
    for c in p:
        t = t.replace(c, c.replace('_', '0').replace('$', '1'))

    p = scrapertools.find_multiple_matches(t, 'j\.(\d{4})')
    for c in p:
        t = re.sub(r'j\.%s' % c, '"' + x[int(c, 2)] + '"', t)

    p = scrapertools.find_multiple_matches(t, '\\"\+j\.(001)\+j\.(\d{3})\+j\.(\d{3})\+')
    for c in p:
        t = re.sub(r'\\"\+j\.%s\+j\.%s\+j\.%s\+' % (c[0], c[1], c[2]), chr(int("".join(c), 2)) + '"+', t)

    p = scrapertools.find_multiple_matches(t, '\\"\+j\.(\d{3})\+j\.(\d{3})\+')
    for c in p:
        t = re.sub(r'\\"\+j\.%s\+j\.%s\+' % (c[0], c[1]), chr(int("".join(c),2)) + '"+', t)

    p = scrapertools.find_multiple_matches(t, 'j\.(\d{3})')
    for c in p:
        t = re.sub(r'j\.%s' % c, '"' + str(int(c, 2)) + '"', t)

    r = re.sub(r'"\+"|\\\\','',t[1:-1])

    return r
