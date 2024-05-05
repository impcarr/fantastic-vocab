import argparse
import logging
import os
import re
import sqlite3
import sys
import time
from html.parser import HTMLParser

import ebooklib
import enchant
from ebooklib import epub

# Create logger
logger = logging.getLogger(__name__)

# Create argument parser
argParser = argparse.ArgumentParser(
    description="Extract text from EPUB files")

def create_aggrecount(cur):
    sql = """create table if not exists aggrecount (word text primary key, count int, en_us boolean, is_num boolean);"""
    cur.execute(sql)

def build_aggrecount(database):
    con = sqlite3.connect(database)
    cur = con.cursor()
    create_aggrecount(cur)
    sql = """insert into aggrecount (word, count, en_us, is_num)
            select word, sum(count), en_us, is_num from megacount group by word, en_us, is_num;"""
    cur.execute(sql)
    con.commit()

def check_title(filepath, title):
    accept = input((f"{title} is the extracted title of the book at {filepath}. Press enter to accept, or N to enter a title manually: "))
    if accept == 'N':
        title = input("Please enter the new title: ")
    return title

def check_author(title, author):
    accept = input((f"{author} is the extracted author of {title}. Press enter to accept, or N to enter the author manually: "))
    if accept == 'N':
        author = input("Please input the new author: ")
    
def naive_counter(words):
    ret = dict()
    for word in words:
        if word in ret:
            ret[word]+=1
        else:
            ret[word] = 1
    return ret

def double_check(word: str,validict: dict) -> bool:
    return validict.check(word) or validict.check(word.capitalize())


def process_text(text: str):
    text = text.replace("’", "'")

    word_pattern = r"\b\w+(?:'\w+)?\b"
    word_regex = re.compile(word_pattern)

    return word_regex.findall(text.lower())
    

def parseCommandLine():
    """Parse command-line arguments"""

    argParser.add_argument('dir_in',
                               action="store",
                               type=str,
                               help='directory with input EPUB files')

    # Parse arguments
    args = argParser.parse_args()

    return args


def errorExit(msg):
    """Print error message and exit"""
    sys.stderr.write("ERROR: " + msg + "\n")
    sys.exit(1)


def errorInfo(msg):
    """Print error message"""
    sys.stderr.write("ERROR: " + msg + "\n")


class HTMLFilter(HTMLParser):
    """
    Source: https://stackoverflow.com/a/55825140/1209004
    """
    text = ""
    def handle_data(self, data):
        self.text += data


def extract_title(book):
    try:
        title = book.get_metadata('DC', 'title')[0][0]
    except Exception as e:
        print(e)
        title = 'Title Not Found'
    return title
    

def extract_author(book):
    try:
        author = book.get_metadata('DC', 'creator')[0][0]
    except Exception as e:
        print(e)
        author = 'Author Not Found'
    return author


def extract_date(book):
    try:
        date = book.get_metadata('DC', 'date')[0][0]
    except Exception:
        date = None
    return date


def create_library(cur):
    sql = """create table if not exists library (filepath text primary key unique, title text, author text, date date);"""
    cur.execute(sql)


def insert_to_library_table(title, author, filepath, date, cur, thorough=False):
    sql = """INSERT OR REPLACE INTO library (filepath, title, author, date)
           VALUES (?, ?, ?, ?);"""
    if thorough:
        title = check_title(filepath, title)
    if thorough:
        author = check_author(title, author)
    try:
        cur.execute(sql, (filepath, title, author, date))
    except sqlite3.OperationalError as e:
        print(e)


def update_library_table(filepath, database='vocab.db'):
    con = sqlite3.connect(database)
    cur = con.cursor()

    create_library(cur)
    
    # Iterate over files in input directory and its subfolders
    for dirpath, dirnames, filenames in os.walk(filepath):
        for filename in [f for f in filenames if f.lower().endswith(".epub")]:
            file_in = os.path.abspath(os.path.join(dirpath, filename))
            try: 
                book = epub.read_epub(file_in)
            except Exception:
                msg = "error parsing " + file_in
                errorInfo(msg)
            
            title = extract_title(book)
            author = extract_author(book)
            date = extract_date(book)
            insert_to_library_table(title, author, file_in, date, cur)
        
    con.commit()


def create_megacount(cur):
    sql = """create table if not exists megacount (filepath text, word text, count int, en_us boolean, is_num boolean, PRIMARY KEY (filepath, word));"""
    cur.execute(sql)


def insert_to_megacount_table(entry: str, number: int, en_us: bool, file_in: str, cur):
    sql = """INSERT OR REPLACE INTO megacount (filepath, word, count, en_us, is_num)
           VALUES (?, ?, ?, ?, ?);"""
    is_num = entry.isnumeric()
    cur.execute(sql, (file_in, entry, number, en_us, is_num))
    


def update_megacount_table(filepath, database='vocab.db'):
    update_start = time.time()
    files = 0
    failures = 0
    con = sqlite3.connect(database)
    cur = con.cursor()

    create_megacount(cur)
    validict = enchant.Dict('en_US')


    for dirpath, dirnames, filenames in os.walk(filepath):
        for filename in [f for f in filenames if f.lower().endswith(".epub")]:
            start = time.time()
            file_in = os.path.abspath(os.path.join(dirpath, filename))
            logger.info(f'Processing {file_in}...')
            try: 
                book = epub.read_epub(file_in)
                content = ""
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        bodyContent = item.get_body_content().decode()
                        f = HTMLFilter()
                        f.feed(bodyContent)
                        content += f.text
                #print(content)
                corpus = process_text(content)
                #print(corpus)
                counts = naive_counter(corpus)

                for entry in counts:
                    insert_to_megacount_table(entry, counts[entry], double_check(entry, validict), file_in, cur)
                files +=1
                logger.info(f'Processed {file_in} in {(time.time()-start):.02f} seconds')
            except Exception:
                failures += 1
                logger.info(f'Failed processing {file_in} at {time.time()}')
    con.commit()
    logger.info(f'Processed {files} files with {failures} failures in {(time.time()-update_start):.02f} seconds')
        

def main():
    """Main command line interface"""

    # Get command line arguments
    args = parseCommandLine()
    dir_in = args.dir_in
    db = 'vocab.db'

    logging.basicConfig(filename='vocab.log', level=logging.INFO)
    

    # Check if input and output directories exist, and exit if not
    if not os.path.isdir(dir_in):
        msg = "input dir doesn't exist"
        errorExit(msg)
    
    
    update_library_table(dir_in, db)
    update_megacount_table(dir_in, db)
    build_aggrecount(db)


if __name__ == "__main__":
    main()