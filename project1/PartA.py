# Assignment 1 - Part A

import sys

"""
Reads in a text file and returns a list of tokens in that file.

Runtime Complexity: O(n) where n is the number of characters in the file.
"""
def tokenize(file_path):
    tokens = []
    current_token = ""
    
    try:
        file = open(file_path, 'r', encoding='utf-8')
        text = file.read()
        file.close()
        
        for char in text:
            if char.isalnum():
                current_token = current_token + char.lower()
            else:
                if current_token != "":
                    tokens.append(current_token)
                    current_token = ""
        
        if current_token != "":
            tokens.append(current_token)
            
    except Exception as error:
        print("Error: Could not read file")
        print("Details:", error)
        sys.exit(1)
    
    return tokens

"""
Counts the number of occurrences of each token in the token list.

Runtime Complexity: O(n) where n is the number of tokens.
"""
def computeWordFrequencies(token_list):
    frequencies = {}
    
    for token in token_list:
        if token in frequencies:
            frequencies[token] = frequencies[token] + 1
        else:
            frequencies[token] = 1
    
    return frequencies

"""
Prints out the word frequency count in descending order.

Runtime Complexity: O(m log m) where m is the number of unique tokens.
"""
def printFrequencies(frequencies):
    items = []

    for token, count in frequencies.items():
        items.append((token, count))
    
    items.sort(key=lambda x: x[1], reverse=True)
    
    for token, count in items:
        print(token + " -> " + str(count))

"""
Main function

Runtime Complexity: O(n + m log m) where n is characters, m is unique tokens.
"""
def main():
    if len(sys.argv) != 2:
        print("Usage: python PartA.py <text_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    tokens = tokenize(file_path)
    frequencies = computeWordFrequencies(tokens)
    printFrequencies(frequencies)

if __name__ == "__main__":
    main()