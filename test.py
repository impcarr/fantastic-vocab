import os
import sys
import csv
import argparse
from html.parser import HTMLParser
import ebooklib
from ebooklib import epub
import enchant
import sqlite3
import time
import collections
import re
import pandas as pd
from datetime import datetime


# Create argument parser
argParser = argparse.ArgumentParser(
    description="Extract text from EPUB files")

def connect_to_db(db):
    con = sqlite3.connect(db)
    return con.cursor()

def init_book_table(book_title, cur):
    try:
        cur.execute(f"CREATE TABLE \"{book_title}\"(title, word, count, en_us)")
    except sqlite3.OperationalError as e:
        print(e)

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


def check_title(filepath, title):
    accept = input((f"{title} is the extracted title of the book at {filepath}. Press enter to accept, or N to enter a title manually: "))
    if accept == 'N':
        title = input(f"Please enter the new title: ")
    return title

def check_author(title, author):
    accept = input((f"{author} is the extracted author of {title}. Press enter to accept, or N to enter the author manually: "))
    if accept == 'N':
        author = input(f"Please input the new author: ")
    
        
def naive_counter(words):
    ret = dict()
    for word in words:
        if word in ret:
            ret[word]+=1
        else:
            ret[word] = 1
    return ret

def double_check(word,validict):
    if validict.check(word):
        return True
    return validict.check(word.capitalize())

def process_text(text):
    word_pattern = r"\b\w+(?:'\w+)?\b"
    word_regex = re.compile(word_pattern)

    return word_regex.findall(text.lower())


def parseCommandLine():
    """Parse command-line arguments"""

    argParser.add_argument('dirIn',
                               action="store",
                               type=str,
                               help='directory with input EPUB files')

    argParser.add_argument('dirOut',
                               action='store',
                               type=str,
                               help='output directory')
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
    #book = epub.read_epub(file)
    return book.get_metadata('DC', 'title')[0][0]

def extract_author(book):
    #book = epub.read_epub(file)
    return book.get_metadata('DC', 'creator')[0][0]

def extract_date(book):
    #book = epub.read_epub()
    return book.get_metadata('DC', 'date')[0][0] 


def extractEbooklib(fileIn, fileOut):
    """Extract text from input file using Ebooklib
    and write result to output file"""

    # Word count
    noWords = 0

    # Try to parse the file with Ebooklib, and report an error message if
    # parsing fails
    try:
        book = epub.read_epub(fileIn)
        content = ""

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                bodyContent = item.get_body_content().decode()
                f = HTMLFilter()
                f.feed(bodyContent)
                content += f.text
                

        successParse = True
    except Exception:
        successParse = False
        msg = "error parsing " + fileIn
        errorInfo(msg)

    # Write extracted text to a text file if parsing was successful    
    if successParse:
        # Word count
        corpus = process_text(content)
        noWords = len(corpus)
        
        counts = naive_counter(corpus)

        #print(word_counts)
        print(f'counts: {counts}')
        validict = enchant.Dict('en_US')
        total_count = 0
        invalids = []
        for word in counts:
            total_count +=1
            if not double_check(word, validict):
                invalids.append(word)
                
        print(f'Total words was {total_count} and invalid was {len(invalids)}')

        #print(f'invalids {invalids}')
        most = max(counts, key=counts.get)
        #print(f'{most},{counts[most]}')

        #print(fileIn)
        

        #exit()
        try:
            with open(fileOut, 'w', encoding='utf-8') as fout:
                fout.write(content)
        except UnicodeError:
            msg = "Unicode error on writing " + fileOut
            errorInfo(msg)    
        except OSError:
            msg = "error writing " + fileOut
            errorInfo(msg)
        except Exception:
            msg = "unknown error writing " + fileOut
            errorInfo(msg)

    return noWords


def main():
    """Main command line interface"""

    # Get command line arguments
    args = parseCommandLine()
    dirIn = args.dirIn
    dirOut = args.dirOut

    # Check if input and output directories exist, and exit if not
    if not os.path.isdir(dirIn):
        msg = "input dir doesn't exist"
        errorExit(msg)

    if not os.path.isdir(dirOut):
        msg = "output dir doesn't exist"
        errorExit(msg)

    # Summary output file
    csvOut = os.path.join(dirOut, "summary-ebooklib.csv")
    csvList = [["fileName", "noWords"]]
    
    
    con = sqlite3.connect('vocab.db')
    cur = con.cursor()

    
    count = 0
    # for dirpath, dirnames, filenames in os.walk(dirIn):
    #     for filename in [f for f in filenames if f.endswith(".epub")]:
    #         print(os.path.join(dirpath, filename))
    #         count+=1
    #print(count)
    bookcheck = pd.DataFrame(columns=['filepath','title','author']) 
    # Iterate over files in input directory and its subfolders
    for dirpath, dirnames, filenames in os.walk(dirIn):
        for filename in [f for f in filenames if f.lower().endswith(".epub")]:
            fIn = os.path.abspath(os.path.join(dirpath, filename))
            bookarr = [fIn]
            #print(fIn)
            book = epub.read_epub(fIn)
            title = extract_title(book)
            author = extract_author(book)
            date = extract_date(book)
            insert_to_library_table(title, author, fIn, date, cur)
            if os.path.isfile(fIn):
                # Get base name and extension for each file
                baseName = os.path.splitext(filename)[0]
                
                
                bookarr.append(baseName)
                bookarr.append(dirpath)
                extension = os.path.splitext(filename)[1]
                

                # Only process files with .epub extension (case-insensitive,
                # just to be safe)
                # if extension.upper() == ".EPUB":
                #     fOutTextract = os.path.join(dirOut, baseName + "_ebooklib.txt")
                #     noWords = extractEbooklib(fIn, fOutTextract)
                #     csvList.append([filename, noWords])
        
    
    # Write summary file

    #init_book_table(baseName, cur)
    con.commit()
    try:
        with open(csvOut, 'w', encoding='utf-8') as csvout:
            csvWriter = csv.writer(csvout)
            for row in csvList:
                csvWriter.writerow(row)
    except UnicodeError:
        msg = "Unicode error on writing " + csvOut
        errorInfo(msg)    
    except OSError:
        msg = "error writing " + csvOut
        errorInfo(msg)
    except Exception:
        msg = "unknown error writing " + csvOut
        errorInfo(msg)


if __name__ == "__main__":
    main()