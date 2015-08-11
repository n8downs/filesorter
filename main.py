import sys
import argparse
import os
import re
import shutil
import time

def getFileExtension(filename):
    parts = filename.split('.')
    return None if len(parts) == 1 else parts[-1]

def parseTitle(original, separator=' '):
    words = original.replace('.', ' ').split()
    for i, word in enumerate(words):
        words[i] = word.lower() if word.lower() in ['the', 'of', 'a', 'or', 'with'] else word.capitalize()
    return separator.join(words)

def normalize(filename, info):
    return '%s.s%se%s.%s' % (parseTitle(info['show'], '.'), '0' + info['season'] if len(info['season']) == 1 else info['season'], info['episode'], getFileExtension(filename))

def isCompleteInfo(info):
    for prop in ['show', 'episode', 'season']:
        if not prop in info:
            return False
    return True

def standard(filename, directory, episodeInfo):
    matches = re.search('(.+)\.(?:s)(\d+)(?:e|ep)(\d+)', filename)
    if matches:
        groups = matches.groups()
        episodeInfo['show'] = groups[0]
        episodeInfo['season'] = groups[1]
        episodeInfo['episode'] = groups[2]

def noSE(filename, directory, episodeInfo):
    matches = re.search('(.+)\.([1-9])([0-9][0-9])[^\d]', filename)
    if matches:
        groups = matches.groups()
        episodeInfo['show'] = groups[0]
        episodeInfo['season'] = groups[1]
        episodeInfo['episode'] = groups[2]

def seasonDir(filename, directory, episodeInfo):
    matches = re.search('(.+)\.season\.(\d+)', directory)
    if matches:
        groups = matches.groups()
        episodeInfo['show'] = groups[0]
        episodeInfo['season'] = groups[1]

def completeDir(filename, directory, episodeInfo):
    if 'show' in episodeInfo:
        return

    matches = re.search('(.+)\.complete', directory)
    if matches:
        groups = matches.groups()
        episodeInfo['show'] = groups[0]

def justSE(filename, directory, episodeInfo):
    matches = re.search('s(\d+)(?:e|ep)(\d+)', filename)
    if matches:
        groups = matches.groups()
        episodeInfo['season'] = groups[0]
        episodeInfo['episode'] = groups[1]

def leadingDot(filename, directory, episodeInfo):
    matches = re.search('^(\d+)\.(\d+)', filename)
    if matches:
        groups = matches.groups()
        episodeInfo['season'] = groups[0]
        episodeInfo['episode'] = groups[1]

def main():
    parser = argparse.ArgumentParser(description='Sort downloaded files for Plex')
    parser.add_argument('--src', dest='source', help='Directory where the source files live.')
    parser.add_argument('--dest', dest='destination', help='Directory where the sorted files should be copied.')
    parser.add_argument('-d', dest='dryRun', action='store_true', help='Print out the files that would be copied without actually doing the work.')

    args = parser.parse_args()
    if args.destination is None or args.source is None:
        print 'Usage: filesorter -d --src [SRC] --dest [DEST]'
        sys.exit(1)

    if not os.path.isdir(args.destination):
        raise Exception('Destination %r is not a directory' % args.destination)

    if not os.path.isdir(args.source):
        raise Exception('Source %r is not a directory' % args.source)

    baseTVPath = os.path.join(args.destination, 'TV')
    if not os.path.exists(baseTVPath):
        os.makedirs(baseTVPath)

    while True:
        print 'Checking source directory %r ...' % (args.source,)
        for dirpath, dirnames, filenames in os.walk(args.source):
            if 'Sample' in dirnames:
                dirnames.remove('Sample')

            for filename in filenames:
                extension = getFileExtension(filename)
                if not extension in ['mkv', 'mp4']:
                    continue

                episodeInfo = {}
                fn = filename.lower().replace(' ', '.')
                directory = os.path.split(dirpath)[-1].lower().replace(' ', '.')

                for heuristic in [standard, noSE, seasonDir, completeDir, justSE, leadingDot]:
                    heuristic(fn, directory, episodeInfo)
                    if isCompleteInfo(episodeInfo):
                        break

                if not isCompleteInfo(episodeInfo):
                    print 'unrecognized filename format: %s' % (os.path.join(dirpath, filename), )
                    continue

                season = 'Season %d' % (int(episodeInfo['season']),)
                show = parseTitle(episodeInfo['show'])

                destDir = os.path.join(baseTVPath, show, season)
                if not os.path.exists(destDir):
                    try:
                        os.makedirs(destDir)
                    except OSError, e:
                        print('failed to make %r', destDir)
                        continue

                source = os.path.join(dirpath, filename)
                dest = os.path.join(destDir, normalize(filename, episodeInfo))
                if os.path.exists(dest) and os.path.getsize(source) != os.path.getsize(dest):
                    os.remove(dest)

                if not os.path.exists(dest):
                    print 'copying\n  %r to\n  %r ...' % (source, dest,),
                    if not args.dryRun:
                        shutil.copyfile(source, dest)
                        print 'done.'
                    else:
                        print '[skipped]'

        sleepMinutes = 15
        print 'Sleeping for %d minutes.' % (sleepMinutes,)
        time.sleep(sleepMinutes * 60)
        print

if __name__ == '__main__':
    main()
