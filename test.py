#! /usr/bin/env python3
"""
EPUB text extraction with Ebooklib demo

Requires Ebooklib:

https://github.com/aerkalov/ebooklib
"""

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

# Create argument parser
argParser = argparse.ArgumentParser(
    description="Extract text from EPUB files")

def init_book_table(book_title):
    con = sqlite3.connect("vocab.db")
    cur = con.cursor()
    try:
        cur.execute(f"CREATE TABLE {book_title}(title, word, count, en_us)")
    except Exception:
        print('Table {book_title} already exists!')

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
        print(f'{most},{counts[most]}')

        #print(fileIn)
        

        exit()
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
    count = 0
    # for dirpath, dirnames, filenames in os.walk(dirIn):
    #     for filename in [f for f in filenames if f.endswith(".epub")]:
    #         print(os.path.join(dirpath, filename))
    #         count+=1
    print(count)  
    # Iterate over files in input directory and its subfolders
    for dirpath, dirnames, filenames in os.walk(dirIn):
        for filename in [f for f in filenames if f.lower().endswith(".epub")]:
            fIn = os.path.abspath(os.path.join(dirpath, filename))
            print(fIn)
            if os.path.isfile(fIn):
                # Get base name and extension for each file
                baseName = os.path.splitext(filename)[0]
                extension = os.path.splitext(filename)[1]

                # Only process files with .epub extension (case-insensitive,
                # just to be safe)
                if extension.upper() == ".EPUB":
                    fOutTextract = os.path.join(dirOut, baseName + "_ebooklib.txt")
                    noWords = extractEbooklib(fIn, fOutTextract)
                    csvList.append([filename, noWords])
        
    
    # Write summary file
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
    init_table("test")
    exit()
    main()