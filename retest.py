import re

def strip_punctuation(text):
    word_pattern = r"\b\w+(?:'\w+)?\b"
    word_regex = re.compile(word_pattern)

    return word_regex.findall(text.lower())

# Example usage
input_text = "Hello, this is a test string! It has hyphenated-words, and other stuff!"
cleaned_text = strip_punctuation(input_text)
print(cleaned_text)
